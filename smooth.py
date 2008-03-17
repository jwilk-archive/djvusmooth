#!/usr/bin/python
# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>

import sys
import os.path

import wx
from djvu import decode

MENU_ICON_SIZE = (16, 16)

wx.EVT_DJVU_MESSAGE = wx.NewId()

class WxDjVuMessage(wx.PyEvent):
	def __init__(self, message):
		wx.PyEvent.__init__(self)
		self.SetEventType(wx.EVT_DJVU_MESSAGE)
		self.message = message

class OpenDialog(wx.FileDialog):

	def __init__(self, parent):
		wx.FileDialog.__init__(self, parent, style = wx.OPEN, wildcard = 'DjVu files (*.djvu, *.djv)|*.djvu;*.djv|All files|*')

PIXEL_FORMAT = decode.PixelFormatRgb()
PIXEL_FORMAT.rows_top_to_bottom = 1
PIXEL_FORMAT.y_top_to_bottom = 1

class PageWidget(wx.ScrolledWindow):

	def __init__(self, *args, **kwargs):
		wx.ScrolledWindow.__init__(self, *args, **kwargs)
		dc = wx.ClientDC(self)
		self.page_job = None
		self._render_mode = decode.RENDER_COLOR
		self._render_text = False
		self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
		self.Bind(wx.EVT_ERASE_BACKGROUND, self.on_erase_background)
		self.Bind(wx.EVT_PAINT, self.on_paint)
		self.need_refresh()

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
	
	def need_refresh(self):
		page_job = self.page_job
		try:
			if page_job is None:
				raise decode.NotAvailable
			dpi = float(page_job.dpi)
			page_width, page_height = page_job.width, page_job.height
			page_width = page_job.width * 100.0 / dpi
			page_height = page_job.height * 100.0 / dpi
			self.page_size = page_width, page_height
			self.SetVirtualSize(self.page_size)
			self.SetScrollRate(1, 1)
		except decode.NotAvailable:
			pass
		self.Refresh()

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
		x, y = self.CalcUnscrolledPosition((0, 0))
		dx, dy  = x % N, y % N
		o = ((x / N) ^ (y / N)) & 1
		oo = o
		y = -dy
		while y < h:
			o = not oo
			x = -dx
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
		x, y = self.CalcUnscrolledPosition((x, y))
		page_job = self.page_job
		try:
			if page_job is None:
				raise decode.NotAvailable
			page_width, page_height = self.page_size
			if x >= page_width:
				raise NotAvailable
			if x + w > page_width:
				w = page_width - x
			if y >= page_height:
				raise NotAvailable
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
			dc.DrawRectangle(x, y, w, h)
			dc.DrawBitmap(image.ConvertToBitmap(), x, y)
		except decode.NotAvailable, ex:
			pass
		dc.EndDrawing()

	def update_drawing(self):
		page_job = self.page_job
		my_width, my_height = self.width, self.height
		dc = wx.BufferedDC(wx.ClientDC(self), self._buffer)
		self.clear_dc(dc, (0, 0, my_width, my_height))
	
	def set_page_job(self, page_job):
		self.page_job = page_job
		self.need_refresh()

class MainWindow(wx.Frame):
	
	def new_menu_item(self, menu, text, help, method, style = wx.ITEM_NORMAL, icon = None):
		item = wx.MenuItem(menu, wx.ID_ANY, text, help, style)
		if icon is not None:
			image = wx.Image(os.path.join('icons', '%s.png' % icon))
			image.Rescale(*MENU_ICON_SIZE)
			item.SetBitmap(image.ConvertToBitmap())
		self.Bind(wx.EVT_MENU, method, item)
		return item

	def __init__(self):
		wx.Frame.__init__(self, None, size=wx.Size(640, 480))
		self.Connect(-1, -1, wx.EVT_DJVU_MESSAGE, self.handle_message)
		self.context = Context(self)
		self.base_title = 'DjVuSmooth'
		self.page_widget = PageWidget(self)
		self.do_open(None)
		if not __debug__:
			sys.excepthook = self.except_hook
		menu_bar = wx.MenuBar()
		menu = wx.Menu()
		menu.AppendItem(self.new_menu_item(menu, '&Open\tCtrl+O', 'Open a DjVu document', self.on_open, icon='file_open'))
		menu.AppendSeparator()
		menu.AppendItem(self.new_menu_item(menu, '&Quit\tCtrl+Q', 'Quit the application', self.on_exit, icon='file_quit'))
		menu_bar.Append(menu, '&File');
		menu = wx.Menu()
		submenu = wx.Menu()
		for text, help, method in \
		[
			('&Color', 'Display everything', self.on_display_everything),
			('&Stencil', 'Display only the document bitonal stencil', self.on_display_stencil),
			('&Foreground', 'Display only the foreground layer', self.on_display_foreground),
			('&Background', 'Display only the foreground layer', self.on_display_background)
		]:
			submenu.AppendItem(self.new_menu_item(submenu, text, help, method, style=wx.ITEM_RADIO))
		submenu.AppendSeparator()
		submenu.AppendItem(self.new_menu_item(submenu, '&Text', 'Display the „hidden” text', self.on_display_text, style=wx.ITEM_CHECK))
		menu.AppendMenu(-1, '&Display', submenu)
		menu.AppendItem(self.new_menu_item(menu, '&Refresh\tCtrl+L', 'Refresh the window', self.on_refresh))
		menu_bar.Append(menu, '&View');
		menu = wx.Menu()
		menu.AppendItem(self.new_menu_item(menu, '&About', 'More information about this program', self.on_about))
		menu_bar.Append(menu, '&Help');
		self.SetMenuBar(menu_bar)
	
	def error_box(self, message, caption = 'Error'):
		wx.MessageBox(message = message, caption = caption, style = wx.OK | wx.ICON_ERROR, parent = self)

	def except_hook(self, type, value, traceback):
		from traceback import format_exception
		message = ''.join(format_exception(type, value, traceback))
		self.error_box(message, 'Unhandled exception: %s [%s]' % (type, value))
	
	def on_exit(self, event):
		self.Close(True)
	
	def on_open(self, event):
		dialog = OpenDialog(self)
		if dialog.ShowModal():
			self.do_open(dialog.GetPath())
	
	def on_display_everything(self, event):
		self.page_widget.render_mode = decode.RENDER_COLOR
	
	def on_display_foreground(self, event):
		self.page_widget.render_mode = decode.RENDER_FOREGROUND

	def on_display_background(self, event):
		self.page_widget.render_mode = decode.RENDER_BACKGROUND
	
	def on_display_stencil(self, event):
		self.page_widget.render_mode = decode.RENDER_BLACK
	
	def on_display_text(self, event):
		self.page_widget.render_text = event.IsChecked()
	
	def on_refresh(self, event):
		self.page_widget.need_refresh()

	def do_open(self, path):
		self.path = path
		if path is None:
			self.document = None
		else:
			self.document = self.context.new_document(decode.FileURI(path))
		self.update_title()
		self.update_page_widget()
	
	def update_page_widget(self, page_job = None):
		if self.document is None:
			page_job = None
		elif page_job is None:
			page_job = self.document.pages[0].decode(wait = False)
		self.page_widget.set_page_job(page_job)

	def update_title(self):
		if self.path is None:
			title = self.base_title
		else:
			title = u'%s — %s' % (self.base_title, os.path.basename(self.path))
			if self.document.decoding_done:
				title += ' [decoding done]'
		self.SetTitle(title)

	def on_about(self, event):
		raise NotImplementedError # TODO
	
	def handle_message(self, event):
		message = event.message
		# TODO: remove debug prints
		if message.document is not self.document:
			print 'IGNORED',
		print self, message
		self.update_title()
		if isinstance(message, (decode.RedisplayMessage, decode.RelayoutMessage)):
			self.update_page_widget(message.page_job)

class Context(decode.Context):

	def __new__(self, window):
		return decode.Context.__new__(self)

	def __init__(self, window):
		decode.Context.__init__(self)
		self.window = window

	def handle_message(self, message):
		wx.PostEvent(self.window, WxDjVuMessage(message))

class SmoothApp(wx.App):

	def OnInit(self):
		window = MainWindow()
		window.Show(True)
		return True

def main():
	app = SmoothApp(0)
	app.MainLoop()

if __name__ == '__main__':
	main()

# vim:ts=4 sw=4
