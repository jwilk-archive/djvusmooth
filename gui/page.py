#!/usr/bin/python
# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>

import wx

from math import floor

from djvu import decode
from models.text import extract_text

PIXEL_FORMAT = decode.PixelFormatRgb()
PIXEL_FORMAT.rows_top_to_bottom = 1
PIXEL_FORMAT.y_top_to_bottom = 1

class Zoom(object):

	def rezoom_on_resize(self):
		raise NotImplementedError

	def get_page_screen_size(self, page_job, viewport_size):
		raise NotImplementedError

class PercentZoom(Zoom):

	def __init__(self, percent = 100):
		self._percent = float(percent)

	def rezoom_on_resize(self):
		return False

	def get_page_screen_size(self, page_job, viewport_size):
		dpi = float(page_job.dpi)
		real_page_size = (page_job.width, page_job.height)
		screen_page_size = tuple(int(t * self._percent / dpi) for t in (real_page_size))
		return screen_page_size

class OneToOneZoom(Zoom):

	def rezoom_on_resize(self):
		return False

	def get_page_screen_size(self, page_job, viewport_size):
		real_page_size = (page_job.width, page_job.height)
		return real_page_size

class StretchZoom(Zoom):

	def rezoom_on_resize(self):
		return True

	def get_page_screen_size(self, page_job, viewport_size):
		return viewport_size

class FitWidthZoom(Zoom):

	def rezoom_on_resize(self):
		return True

	def get_page_screen_size(self, page_job, (viewport_width, viewport_height)):
		real_width, real_height = (page_job.width, page_job.height)
		ratio = 1.0 * real_height / real_width
		return (viewport_width, int(viewport_width * ratio))

class FitPageZoom(Zoom):

	def rezoom_on_resize(self):
		return True

	def get_page_screen_size(self, page_job, (viewport_width, viewport_height)):
		real_width, real_height  = (page_job.width, page_job.height)
		ratio = 1.0 * real_height / real_width
		screen_height = int(viewport_width * ratio)
		if screen_height <= viewport_height:
			screen_width = viewport_width
		else:
			screen_width = int(viewport_height / ratio)
			screen_height = viewport_height
		return (screen_width, screen_height)

class PageWidget(wx.Panel):

	def __init__(self, *args, **kwargs):
		wx.Panel.__init__(self, *args, **kwargs)
		self._initial_size = self.GetSize()
		dc = wx.ClientDC(self)
		self._render_mode = decode.RENDER_COLOR
		self._render_text = False
		self._zoom = PercentZoom()
		self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
		self.Bind(wx.EVT_ERASE_BACKGROUND, self.on_erase_background)
		self.Bind(wx.EVT_PAINT, self.on_paint)
		self.page = None
		self._checkboard_brush = wx.Brush((0x88,) * 3, wx.SOLID)
		self._text_color = wx.Color(0, 0, 0x88)
		self._text_pen = wx.Pen(self._text_color, 1)

	def on_parent_resize(self, event):
		if self._zoom.rezoom_on_resize():
			self.zoom = self._zoom
		event.Skip()

	@apply
	def render_mode():
		def get(self):
			return self._render_mode
		def set(self, value):
			self._render_mode = value
			self.Refresh()
		return property(get, set)

	@apply
	def render_text():
		def get(self):
			return self._render_text
		def set(self, value):
			self._render_text = value
			self.Refresh()
		return property(get, set)
	
	def refresh_text(self):
		if self.render_text:
			self.Refresh()
	
	@apply
	def zoom():
		def get(self):
			return self._zoom
		def set(self, value):
			self._zoom = value
			self.page = True
		return property(get, set)

	def on_paint(self, event):
		dc = wx.PaintDC(self)
		self.PrepareDC(dc)
		self.draw(dc, self.GetUpdateRegion())

	@apply
	def page():
		def set(self, page):
			try:
				if page is None:
					raise decode.NotAvailable
				elif page is True:
					page_job = self._page_job
					page_text = self._page_text
				else:
					page_job = page.page_job
					page_text = page.text
				real_page_size = (page_job.width, page_job.height)
				viewport_size = tuple(self.GetParent().GetSize())
				screen_page_size = self._zoom.get_page_screen_size(page_job, viewport_size)
				xform_screen_to_real = decode.AffineTransform((0, 0) + real_page_size, (0, 0) + screen_page_size)
				xform_screen_to_real.mirror_y()
				self.set_size(screen_page_size)
			except decode.NotAvailable:
				screen_page_size = -1, -1
				xform_screen_to_real = decode.AffineTransform((0, 0, 1, 1), (0, 0, 1, 1))
				page_job = None
				page_text = None
			self._screen_page_size = screen_page_size
			self._xform_screen_to_real = xform_screen_to_real
			self._page_job = page_job
			self._page_text = page_text
			if page is None:
				self.set_size(self._initial_size)
			self.Refresh()
		return property(fset = set)

	def set_size(self, size):
		self.SetSize(size)
		self.SetBestFittingSize(size)
		self.GetParent().Layout()
		self.GetParent().SetupScrolling()

	def on_erase_background(self, event):
		dc = event.GetDC()
		rect = self.GetUpdateRegion().GetBox()
		if not dc:
			dc = wx.ClientDC(self)
			dc.SetClippingRect(rect)
		self._clear_dc(dc, rect)

	def _clear_dc(self, dc, rect):
		N = 16
		dc.Clear()
		dc.SetBrush(self._checkboard_brush)
		dc.SetPen(wx.TRANSPARENT_PEN)
		x0, y0, w, h = rect
		x1 = (x0 + w + N - 1) // N * N
		y1 = (y0 + h + N - 1) // N * N
		x0 = x0 // N * N
		y0 = y0 // N * N
		o = oo = (x0//N ^ y0//N) & 1
		y = y0
		while y < y1:
			o = not oo
			x = x0
			while x < x1:
				if o:
					dc.DrawRectangle(x, y, N, N)
				x += N
				o = not o
			y += N
			oo = not oo
		
	def draw(self, dc, region):
		dc.BeginDrawing()
		x, y, w, h = region.GetBox()
		page_job = self._page_job
		page_text = self._page_text
		xform_screen_to_real = self._xform_screen_to_real
		try:
			if page_job is None:
				raise decode.NotAvailable
			page_width, page_height = self._screen_page_size
			if x >= page_width:
				raise decode.NotAvailable
			if x + w > page_width:
				w = page_width - x
			if y >= page_height:
				raise decode.NotAvailable
			if y + h > page_height:
				h = page_height - y
			render_mode = self.render_mode
			if self.render_mode is None:
				dc.SetBrush(wx.WHITE_BRUSH)
				dc.SetPen(wx.TRANSPARENT_PEN)
				dc.DrawRectangle(x, y, w, h)
			else:
				data = page_job.render(
					self.render_mode,
					(0, 0, page_width, page_height),
					(x, y, w, h),
					PIXEL_FORMAT,
					1
				)
				image = wx.EmptyImage(w, h)
				image.SetData(data)
				dc.DrawBitmap(image.ConvertToBitmap(), x, y)
		except decode.NotAvailable, ex:
			pass
		if self.render_text and self._page_text is not None:
			try:
				dc.SetBrush(wx.TRANSPARENT_BRUSH)
				dc.SetPen(self._text_pen)
				dc.SetTextForeground(self._text_color)
				sexpr = self._page_text.sexpr
				rx, ry, rxp, ryp = x, y, x + w, y + h
				for (x, y, xp, yp), text in extract_text(sexpr):
					rect = (x, y, xp - x, yp - y)
					x, y, w, h = xform_screen_to_real(rect)
					if x > rxp or x + w < rx:
						continue
					if y > ryp or y + h < ry:
						continue
					dc.DrawRectangle(x, y, w, h)
					font = dc.GetFont()
					font_size = h
					font.SetPixelSize((font_size, font_size))
					dc.SetFont(font)
					w1, h1 = dc.GetTextExtent(text)
					if w1 > w:
						font_size = floor(font_size * 1.0 * w / w1)
						font.SetPixelSize((font_size, font_size))
						dc.SetFont(font)
						w1, h1 = dc.GetTextExtent(text)
					dc.DrawText(text, x, y)
			except decode.NotAvailable, ex:
				pass
		dc.EndDrawing()

# vim:ts=4 sw=4
