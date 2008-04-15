#!/usr/bin/python
# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>

import wx
import wx.lib.ogl

from math import floor

from djvu import decode
import models.text

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

class PageImage(wx.lib.ogl.RectangleShape):

	def __init__(self, parent, page_job, real_page_size, viewport_size, screen_page_size, xform_screen_to_real, render_mode, zoom):
		self._render_mode = render_mode
		self._zoom = zoom
		self._screen_page_size = screen_page_size
		self._xform_screen_to_real = xform_screen_to_real
		self._page_job = page_job
		wx.lib.ogl.RectangleShape.__init__(self, *screen_page_size)
		self.SetX(self._width // 2)
		self.SetY(self._height // 2)

	def OnDraw(self, dc):
		x, y, w, h = self.GetCanvas().GetUpdateRegion().GetBox()
		if w < 0 or h < 0:
			# This is not a regular refresh. 
			# So just see what might have been overwritten.
			x, y, w, h = dc.GetBoundingBox()
		dc.BeginDrawing()
		page_job = self._page_job
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
			render_mode = self._render_mode
			if render_mode is None:
				raise decode.NotAvailable
			else:
				data = page_job.render(
					render_mode,
					(0, 0, page_width, page_height),
					(x, y, w, h),
					PIXEL_FORMAT,
					1
				)
				image = wx.EmptyImage(w, h)
				image.SetData(data)
				dc.DrawBitmap(image.ConvertToBitmap(), x, y)
		except decode.NotAvailable, ex:
			dc.SetBrush(wx.WHITE_BRUSH)
			dc.SetPen(wx.TRANSPARENT_PEN)
			dc.DrawRectangle(x, y, w, h)
		dc.EndDrawing()

class TextShape(wx.lib.ogl.RectangleShape):

	def __init__(self, node, xform_screen_to_real):
		wx.lib.ogl.RectangleShape.__init__(self, 100, 100)
		self._xform_screen_to_real = xform_screen_to_real
		self._node = node
		self._update_size()
		self._text_color = wx.Color(0, 0, 0x88)
		self._text_pen = wx.Pen(self._text_color, 1)
		# XXX self.AddText(text)
		self.SetPen(self._text_pen)
		self.SetBrush(wx.TRANSPARENT_BRUSH)
	
	def _update_size(self):
		x, y, w, h = self._xform_screen_to_real(self._node.rect)
		self.SetSize(w, h)
		self.SetX(x + w // 2)
		self.SetY(y + h // 2)

class PageTextCallback(models.text.PageTextCallback):

	def __init__(self, widget):
		self._widget = widget
	
	def notify_node_change(self, node):
		self._widget.page = True # FIXME: something lighter here
		
	def notify_tree_change(self, node):
		self._widget.page = True

class PageWidget(wx.lib.ogl.ShapeCanvas):

	def __init__(self, parent):
		wx.lib.ogl.ShapeCanvas.__init__(self, parent)
		self._initial_size = self.GetSize()
		self.SetBackgroundColour(wx.WHITE)
		self._diagram = wx.lib.ogl.Diagram()
		self.SetDiagram(self._diagram)
		self._diagram.SetCanvas(self)
		self._image = None
		self._text_shapes = []
		dc = wx.ClientDC(self)
		self.PrepareDC(dc)
		self._render_mode = decode.RENDER_COLOR
		self._render_text = False
		self._zoom = PercentZoom()
		self.page = None
	
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
			self.page = True
		return property(get, set)

	@apply
	def render_text():
		def get(self):
			return self._render_text
		def set(self, value):
			self._render_text = value
			self.setup_text_shapes()
			self.recreate_shapes()
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

	@apply
	def page():
		def set(self, page):
			try:
				if page is None:
					raise decode.NotAvailable
				elif page is True:
					page_job = self._page_job
					page_text = self._page_text
					callback = self._callback
				else:
					page_job = page.page_job
					callback = PageTextCallback(self)
					page_text = page.text
					page_text.register_callback(callback)
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
				need_recreate_text = True
				callback = None
			self._screen_page_size = screen_page_size
			self._xform_screen_to_real = xform_screen_to_real
			self._page_job = page_job
			self._page_text = page_text
			self._callback = callback
			if page is None:
				self.set_size(self._initial_size)
			if self._image is not None:
				self._image.Delete()
				self._image = None
			if page_job is not None:
				image = PageImage(self,
					page_job = page_job,
					real_page_size = real_page_size,
					viewport_size = viewport_size,
					screen_page_size = screen_page_size,
					xform_screen_to_real = xform_screen_to_real,
					render_mode = self.render_mode,
					zoom = self.zoom)
				image.SetDraggable(False, False)
				self._image = image
			self.setup_text_shapes()
			self.recreate_shapes()
		return property(fset = set)

	def recreate_shapes(self):
		self.remove_all_shapes()
		image = self._image
		if image is not None:
			self.add_shape(image)
		if self.render_text:
			for shape in self._text_shapes:
				self.add_shape(shape)
		self.Refresh()

	def add_shape(self, shape):
		shape.SetCanvas(self)
		shape.Show(True)
		self._diagram.AddShape(shape)
	
	def remove_all_shapes(self):
		self._diagram.RemoveAllShapes()

	def set_size(self, size):
		self.SetSize(size)
		self.SetBestFittingSize(size)
		self.GetParent().Layout()
		self.GetParent().SetupScrolling()

	def setup_text_shapes(self):
		self._text_shapes = []
		if not self.render_text or self._page_text is None:
			return
		xform_screen_to_real = self._xform_screen_to_real
		try:
			self._text_shapes = [TextShape(node, xform_screen_to_real) for node in self._page_text.get_leafs()]
				# font = dc.GetFont()
				# font_size = h
				# font.SetPixelSize((font_size, font_size))
				# dc.SetFont(font)
				# w1, h1 = dc.GetTextExtent(text)
				# if w1 > w:
				# 	font_size = floor(font_size * 1.0 * w / w1)
				# 	font.SetPixelSize((font_size, font_size))
				# 	dc.SetFont(font)
				# 	w1, h1 = dc.GetTextExtent(text)
		except decode.NotAvailable, ex:
			self._text_shapes = []

__all__ = (
	'Zoom', 'PercentZoom', 'OneToOneZoom', 'StretchZoom', 'FitWidthZoom', 'FitPageZoom',
	'PageWidget'
)

# vim:ts=4 sw=4
