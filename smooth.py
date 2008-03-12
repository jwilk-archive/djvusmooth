#!/usr/bin/python
# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>

import sys
import os.path

import wx
import djvu.decode

MENU_ICON_SIZE = (16, 16)

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
		wx.Frame.__init__(self, None, -1, title='DjVuSmooth', size=wx.Size(640, 480))
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
		raise NotImplementedError # TODO

	def on_about(self, event):
		raise NotImplementedError # TODO
				
class SmoothApp(wx.App):

	def OnInit(self):
		self.context = djvu.decode.Context()
		window = MainWindow()
		window.Show(True)
		return True

def main():
	app = SmoothApp(0)
	app.MainLoop()

if __name__ == '__main__':
	main()

# vim:ts=4 sw=4
