#!/usr/bin/python
# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>

import wx

from djvu import decode

PIXEL_FORMAT = decode.PixelFormatRgb()
PIXEL_FORMAT.rows_top_to_bottom = 1
PIXEL_FORMAT.y_top_to_bottom = 1

class PageWidget(wx.Panel):

	def __init__(self, *args, **kwargs):
		wx.Panel.__init__(self, *args, **kwargs)
		dc = wx.ClientDC(self)
		self._render_mode = decode.RENDER_COLOR
		self._render_text = False
		self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
		self.Bind(wx.EVT_ERASE_BACKGROUND, self.on_erase_background)
		self.Bind(wx.EVT_PAINT, self.on_paint)
		self._page_job = None
		self._page_text = None
		self._page_size = -1, -1

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
				page_job = page.decode(wait = False)
				page_text = page.text
				dpi = float(page_job.dpi)
				page_size = tuple(t * 100.0 / dpi for t in (page_job.width, page_job.height))
				self.SetSize(page_size)
				self.SetBestFittingSize(page_size)
				self.GetParent().Layout()
				self.GetParent().SetupScrolling()
			except decode.NotAvailable:
				page_size = -1, -1
				page_job = None
				page_text = None
			self._page_size = page_size
			self._page_job = page_job
			self._page_text = page_text
			self.Refresh()
		return property(fset = set)

	def on_erase_background(self, evt):
		dc = evt.GetDC()
		if not dc:
			dc = wx.ClientDC(self)
			rect = self.GetUpdateRegion().GetBox()
			dc.SetClippingRect(rect)
		self.clear_dc(dc)

	def clear_dc(self, dc):
		N = 16
		dc.Clear()
		dc.SetBrush(wx.Brush((0x80, 0x80, 0x80)))
		dc.SetPen(wx.Pen((0x80, 0x80, 0x80)))
		w, h = self.GetClientSize()
		o = oo = False
		y = 0
		while y < h:
			o = not oo
			x = 0
			while x < w:
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
		try:
			if page_job is None:
				raise decode.NotAvailable
			page_width, page_height = self._page_size
			if x >= page_width:
				raise decode.NotAvailable
			if x + w > page_width:
				w = page_width - x
			if y >= page_height:
				raise decode.NotAvailable
			if y + h > page_height:
				h = page_height - y
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
		dc.EndDrawing()

	def update_drawing(self):
		page_job = self._page_job
		my_width, my_height = self.width, self.height
		dc = wx.BufferedDC(wx.ClientDC(self), self._buffer)
		self.clear_dc(dc, (0, 0, my_width, my_height))

# vim:ts=4 sw=4
