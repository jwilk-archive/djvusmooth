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

class PageWidget(wx.Panel):

	def __init__(self, *args, **kwargs):
		wx.Panel.__init__(self, *args, **kwargs)
		self.page_job = None
		self.Bind(wx.EVT_PAINT, self.on_paint)
		self.Bind(wx.EVT_SIZE, self.on_size)
		self.Bind(wx.EVT_ERASE_BACKGROUND, lambda *args, **kwargs: None)
		self.on_size(None)
	
	def on_size(self, event):
		self.width, self.height = self.GetClientSizeTuple()
		self._buffer = wx.EmptyBitmap(self.width, self.height)
		self.update_drawing()
	
	def on_paint(self, event):
		wx.BufferedPaintDC(self, self._buffer)

	def clear_dc(self, dc):
		N = 16
		dc.Clear()
		dc.SetBrush(wx.Brush((0x80, 0x80, 0x80)))
		dc.SetPen(wx.Pen((0x80, 0x80, 0x80)))
		for y in xrange((self.height + N - 1) // N):
			for x in xrange((self.width + N - 1) // N):
				if (x ^ y) & 1:
					continue
				dc.DrawRectangle(x * N, y * N, N, N)
		
	def update_drawing(self):
		page_job = self.page_job
		my_width, my_height = self.width, self.height
		dc = wx.BufferedDC(wx.ClientDC(self), self._buffer)
		self.clear_dc(dc)
		try:
			# TODO: don't render the whole area,
			# just the part that needs to be redrawn
			if page_job is None:
				raise decode.NotAvailable
			dpi = float(page_job.dpi)
			page_width, page_height = page_job.width, page_job.height
			page_width = page_job.width * 100.0 / dpi
			page_height = page_job.height * 100.0 / dpi
			my_width = min(my_width, page_width)
			my_height = min(my_height, page_height)
			data = page_job.render(
				decode.RENDER_COLOR,
				(0, 0, page_width, page_height),
				(0, 0, my_width, my_height),
				PIXEL_FORMAT,
				1
			)
			image = wx.EmptyImage(my_width, my_height)
			image.SetData(data)
			dc.DrawBitmap(image.ConvertToBitmap(), 0, 0)
		except decode.NotAvailable, ex:
			pass
	
	def set_page_job(self, page_job):
		self.page_job = page_job
		self.on_size(None)

class MainWindow(wx.Frame):
	
	def new_menu_item(self, menu, text, help, method, icon = None):
		item = wx.MenuItem(menu, wx.ID_ANY, text, help)
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
		menu.AppendItem(self.new_menu_item(menu, '&Open\tCtrl+O', 'Open a DjVu document', self.on_open, 'file_open'))
		menu.AppendSeparator()
		menu.AppendItem(self.new_menu_item(menu, '&Quit\tCtrl+Q', 'Quit the application', self.on_exit, 'file_quit'))
		menu_bar.Append(menu, '&File');
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
