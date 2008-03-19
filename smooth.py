#!/usr/bin/python
# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>

import sys
import os.path

import wx
import wx.lib.scrolledpanel

from djvu import decode

from gui.page import PageWidget

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

class MainWindow(wx.Frame):
	
	def new_menu_item(self, menu, text, help, method, style = wx.ITEM_NORMAL, icon = None):
		item = wx.MenuItem(menu, wx.ID_ANY, text, help, style)
		if icon is not None:
			bitmap = wx.ArtProvider_GetBitmap(icon, wx.ART_MENU, MENU_ICON_SIZE)
			item.SetBitmap(bitmap)
		self.Bind(wx.EVT_MENU, method, item)
		return item

	def __init__(self):
		wx.Frame.__init__(self, None, size=wx.Size(640, 480))
		self.Connect(-1, -1, wx.EVT_DJVU_MESSAGE, self.handle_message)
		self.context = Context(self)
		self.base_title = 'DjVuSmooth'
		self.scrolled_panel = wx.lib.scrolledpanel.ScrolledPanel(self, -1)
		sizer = wx.BoxSizer(wx.VERTICAL)
		self.scrolled_panel.SetSizer(sizer)
		self.scrolled_panel.SetAutoLayout(True)
		self.scrolled_panel.SetupScrolling()
		self.page_widget = PageWidget(self.scrolled_panel)
		sizer.Add(self.page_widget, 0, wx.ALL | wx.EXPAND)
		if not __debug__:
			sys.excepthook = self.except_hook
		menu_bar = wx.MenuBar()
		menu = wx.Menu()
		menu.AppendItem(self.new_menu_item(menu, '&Open\tCtrl+O', 'Open a DjVu document', self.on_open, icon=wx.ART_FILE_OPEN))
		menu.AppendSeparator()
		menu.AppendItem(self.new_menu_item(menu, '&Quit\tCtrl+Q', 'Quit the application', self.on_exit, icon=wx.ART_QUIT))
		menu_bar.Append(menu, '&File');
		menu = wx.Menu()
		menu.AppendItem(self.new_menu_item(menu, '&Metadata\tCtrl+M', 'Edit the document or page metadata', self.on_edit_metadata))
		menu_bar.Append(menu, '&Edit');
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
		for text, help, method, icon in \
		[
			('&Refresh\tCtrl+L', 'Refresh the window', self.on_refresh, None),
			('&Next page\tPgDn', '', self.on_next_page, wx.ART_GO_UP),
			('&Previous page\tPgUp', '', self.on_previous_page, wx.ART_GO_DOWN),
		]:
			menu.AppendItem(self.new_menu_item(menu, text, help, method, icon=icon))
		menu_bar.Append(menu, '&View');
		menu = wx.Menu()
		menu.AppendItem(self.new_menu_item(menu, '&About', 'More information about this program', self.on_about))
		menu_bar.Append(menu, '&Help');
		self.SetMenuBar(menu_bar)
		self.metadata_dialog = wx.Dialog(self, -1, 'Edit metadata')
		self.do_open(None)
	
	def enable_edit_menu(self, enable=True):
		self.GetMenuBar().EnableTop(1, enable)

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
		self.Refresh()

	def on_next_page(self, event):
		if self.document is None:
			return
		page_no = self.page_no + 1
		if page_no >= len(self.document.pages):
			return
		self.page_no += page_no
		self.update_page_widget(True)

	def on_previous_page(self, event):
		if self.document is None:
			return
		page_no = self.page_no - 1
		if page_no < 0:
			return
		self.page_no = page_no
		self.update_page_widget(True)

	def on_edit_metadata(self, event):
		annotations = self.document.annotations
		annotations.wait()
		print annotations.metadata.items()
		self.metadata_dialog.ShowModal()

	def do_open(self, path):
		self.path = path
		self.page_no = 0
		if path is None:
			self.document = None
			self.enable_edit_menu(False)
		else:
			self.document = self.context.new_document(decode.FileURI(path))
			self.enable_edit_menu(True)
		self.update_title()
		self.update_page_widget(new_page_job=True)
	
	def update_page_widget(self, new_page_job=False):
		if self.document is None:
			self.page_job = None
		elif self.page_job is None or new_page_job:
			self.page_job = self.document.pages[self.page_no].decode(wait = False)
		self.page_widget.page_job = self.page_job

	def update_title(self):
		if self.path is None:
			title = self.base_title
		else:
			title = u'%s — %s' % (self.base_title, os.path.basename(self.path))
		self.SetTitle(title)

	def on_about(self, event):
		raise NotImplementedError # TODO
	
	def handle_message(self, event):
		message = event.message
		# TODO: remove debug prints
		if message.document is not self.document:
			print 'IGNORED', message
		self.update_title()
		if isinstance(message, (decode.RedisplayMessage, decode.RelayoutMessage)):
			if self.page_job is message.page_job:
				self.update_page_widget()

class Context(decode.Context):

	def __new__(self, window):
		return decode.Context.__new__(self)

	def __init__(self, window):
		decode.Context.__init__(self)
		self.window = window

	def handle_message(self, message):
		wx.PostEvent(self.window, WxDjVuMessage(message))

class SmoothApp(wx.App):

	def __init__(self, argv):
		self._argv = argv
		wx.App.__init__(self)

	def OnInit(self):
		window = MainWindow()
		window.Show(True)
		if self._argv:
			window.do_open(self._argv.pop(0))
		return True

def main(argv):
	app = SmoothApp(argv)
	app.MainLoop()

if __name__ == '__main__':
	from sys import argv
	main(argv[1:])

# vim:ts=4 sw=4
