# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>

APPLICATION_NAME = 'DjVuSmooth'
LICENSE = 'GPL-2'
__version__ = '0.1'
__author__ = 'Jakub Wilk <ubanus@users.sf.net>'

import sys
import os.path
import threading
from Queue import Queue, Empty as QueueEmpty

import wx
import wx.lib.scrolledpanel

from djvu import decode
import djvu.const

from djvused import StreamEditor
from gui.page import PageWidget, PercentZoom, OneToOneZoom, StretchZoom, FitWidthZoom, FitPageZoom
from gui.metadata import MetadataDialog
import models.metadata

MENU_ICON_SIZE = (16, 16)
DJVU_WILDCARD = 'DjVu files (*.djvu, *.djv)|*.djvu;*.djv|All files|*'

wx.EVT_DJVU_MESSAGE = wx.NewId()

class WxDjVuMessage(wx.PyEvent):
	def __init__(self, message):
		wx.PyEvent.__init__(self)
		self.SetEventType(wx.EVT_DJVU_MESSAGE)
		self.message = message

class GaugeProgressDialog(wx.ProgressDialog):

	def __init__(self, title, message, maximum = 100, parent = None, style = wx.PD_AUTO_HIDE | wx.PD_APP_MODAL):
		wx.ProgressDialog.__init__(self, title, message, maximum, parent, style)
		self.__max = maximum
		self.__n = 0
		
	try:
		wx.ProgressDialog.Pulse
	except AttributeError:
		def Pulse(self):
			self.__n = (self.__n + 1) % self.__max
			self.Update(self.__n)

class OpenDialog(wx.FileDialog):

	def __init__(self, parent):
		wx.FileDialog.__init__(self, parent, style = wx.OPEN, wildcard=DJVU_WILDCARD)

class MetadataModel(models.metadata.Metadata):
	def __init__(self, document):
		models.metadata.Metadata.__init__(self)
		self._document = document

	def acquire_metadata(self, n):
		document_annotations = self._document.annotations
		document_annotations.wait()
		document_metadata = document_annotations.metadata
		if n == models.metadata.SHARED_ANNOTATIONS_PAGENO:
			result = document_metadata
		else:
			page_annotations = self._document.pages[n].annotations
			page_annotations.wait()
			page_metadata = page_annotations.metadata
			result = {}
			for k, v in page_metadata.iteritems():
				if k not in document_metadata:
					pass
				elif v != document_metadata[k]:
					pass
				else:
					continue
				result[k] = v
		return result

class MainWindow(wx.Frame):
	
	def new_menu_item(self, menu, text, help, method, style = wx.ITEM_NORMAL, icon = None, id = wx.ID_ANY):
		item = wx.MenuItem(menu, id, text, help, style)
		if icon is not None:
			bitmap = wx.ArtProvider_GetBitmap(icon, wx.ART_MENU, MENU_ICON_SIZE)
			item.SetBitmap(bitmap)
		self.Bind(wx.EVT_MENU, method, item)
		return item

	def __init__(self):
		wx.Frame.__init__(self, None, size=wx.Size(640, 480))
		self.Connect(-1, -1, wx.EVT_DJVU_MESSAGE, self.handle_message)
		self.context = Context(self)
		self.splitter = wx.SplitterWindow(self, -1, style = wx.SP_LIVE_UPDATE)
		self.sidebar = wx.Panel(self.splitter, -1, size = (5, 5))
		self.scrolled_panel = wx.lib.scrolledpanel.ScrolledPanel(self.splitter, -1)
		self.splitter._default_position = 160
		self.splitter.SetSashGravity(0.1)
		self.do_show_sidebar()
		self.do_hide_sidebar()
		sizer = wx.BoxSizer(wx.VERTICAL)
		self.scrolled_panel.SetSizer(sizer)
		self.scrolled_panel.SetAutoLayout(True)
		self.scrolled_panel.SetupScrolling()
		self.page_widget = PageWidget(self.scrolled_panel)
		self.scrolled_panel.Bind(wx.EVT_SIZE, self.page_widget.on_parent_resize)
		sizer.Add(self.page_widget, 0, wx.ALL | wx.EXPAND)
		if not __debug__:
			sys.excepthook = self.except_hook
		self.editable_menu_items = []
		menu_bar = wx.MenuBar()
		menu = wx.Menu()
		menu.AppendItem(self.new_menu_item(menu, '&Open\tCtrl+O', 'Open a DjVu document', self.on_open, icon=wx.ART_FILE_OPEN))
		save_menu_item = self.new_menu_item(menu, '&Save\tCtrl+S', 'Save the document', self.on_save, icon=wx.ART_FILE_SAVE)
		close_menu_item = self.new_menu_item(menu, '&Close\tCtrl+W', 'Close the document', self.on_close, id=wx.ID_CLOSE)
		menu.AppendItem(save_menu_item)
		self.editable_menu_items += save_menu_item, close_menu_item
		menu.AppendSeparator()
		menu.AppendItem(self.new_menu_item(menu, '&Quit\tCtrl+Q', 'Quit the application', self.on_exit, icon=wx.ART_QUIT))
		menu_bar.Append(menu, '&File');
		menu = wx.Menu()
		menu.AppendItem(self.new_menu_item(menu, '&Metadata\tCtrl+M', 'Edit the document or page metadata', self.on_edit_metadata))
		menu_bar.Append(menu, '&Edit');
		menu = wx.Menu()
		submenu = wx.Menu()
		for text, help, zoom, id in \
		[
			('Fit &width', 'Set magnification to fit page width', FitWidthZoom(), None),
			('Fit &page', 'Set magnification to fit page', FitPageZoom(), wx.ID_ZOOM_FIT),
			('&Stretch', 'Stretch the image to the window size', StretchZoom(), None),
			('One to &one', 'Set full resolution magnification.', OneToOneZoom(), wx.ID_ZOOM_100),
		]:
			submenu.AppendItem(self.new_menu_item(submenu, text, help, self.on_zoom(zoom), style=wx.ITEM_RADIO, id = id or wx.ID_ANY))
		submenu.AppendSeparator()
		for percent in 300, 200, 150, 100, 75, 50:
			item = self.new_menu_item(
				submenu,
				'%d%%' % percent,
				'Magnify %d%%' % percent,
				self.on_zoom(PercentZoom(percent)),
				style=wx.ITEM_RADIO
			)
			submenu.AppendItem(item)
			if percent == 100:
				item.Check()
		menu.AppendMenu(-1, '&Zoom', submenu)

		submenu = wx.Menu()
		for text, help, method in \
		[
			('&Color', 'Display everything', self.on_display_everything),
			('&Stencil', 'Display only the document bitonal stencil', self.on_display_stencil),
			('&Foreground', 'Display only the foreground layer', self.on_display_foreground),
			('&Background', 'Display only the foreground layer', self.on_display_background),
			('&None', 'Neither display forgeground layer nor background layer', self.on_display_none)
		]:
			submenu.AppendItem(self.new_menu_item(submenu, text, help, method, style=wx.ITEM_RADIO))
		submenu.AppendSeparator()
		submenu.AppendItem(self.new_menu_item(submenu, '&Text', 'Display the „hidden” text', self.on_display_text, style=wx.ITEM_CHECK))
		menu.AppendMenu(-1, '&Display', submenu)
		menu.AppendItem(self.new_menu_item(menu, '&Refresh\tCtrl+L', 'Refresh the window', self.on_refresh))
		menu_bar.Append(menu, '&View')
		menu = wx.Menu()
		for text, help, method, icon in \
		[
			('&First page\tCtrl-Home', 'Jump to first document page', self.on_first_page, None),
			('&Previous page\tPgUp', 'Jump to previous document page', self.on_previous_page, wx.ART_GO_UP),
			('&Next page\tPgDn', 'Jump to next document page', self.on_next_page, wx.ART_GO_DOWN),
			('&Last page\tCtrl-End', 'Jump to last document page', self.on_last_page, None),
		]:
			menu.AppendItem(self.new_menu_item(menu, text, help, method, icon = icon))
		menu_bar.Append(menu, '&Go');
		menu = wx.Menu()
		menu.AppendItem(self.new_menu_item(menu, 'Show &sidebar\tF9', 'Show/side the sidebar', self.on_show_sidebar, style=wx.ITEM_CHECK))
		menu_bar.Append(menu, '&Settings');
		menu = wx.Menu()
		menu.AppendItem(self.new_menu_item(menu, '&About\tF1', 'More information about this program', self.on_about, id=wx.ID_ABOUT))
		menu_bar.Append(menu, '&Help');
		self.SetMenuBar(menu_bar)
		self.dirty = False
		self.do_open(None)
	
	def enable_edit(self, enable=True):
		for i in 1, 3:
			self.GetMenuBar().EnableTop(i, enable)
		for menu_item in self.editable_menu_items:
			menu_item.Enable(enable)

	def error_box(self, message, caption = 'Error'):
		wx.MessageBox(message = message, caption = caption, style = wx.OK | wx.ICON_ERROR, parent = self)

	def except_hook(self, type, value, traceback):
		from traceback import format_exception
		message = ''.join(format_exception(type, value, traceback))
		self.error_box(message, 'Unhandled exception: %s [%s]' % (type, value))
	
	def on_exit(self, event):
		if self.do_open(None):
			self.Destroy()
	
	def on_open(self, event):
		dialog = OpenDialog(self)
		try:
			if dialog.ShowModal():
				self.do_open(dialog.GetPath())
		finally:
			dialog.Destroy()

	def on_close(self, event):
		self.do_open(None)

	def on_save(self, event):
		self.do_save()
	
	def do_save(self):
		if not self.dirty:
			return
		queue = Queue()
		sed = StreamEditor(self.path, autosave=True)
		if self.metadata_model is not None:
			self.metadata_model.export(sed)
		def job():
			sed.commit()
			queue.put(True)
		thread = threading.Thread(target = job)
		thread.start()
		dialog = None
		try:
			try:
				queue.get(block = True, timeout = 0.1)
				return
			except QueueEmpty:
				dialog = GaugeProgressDialog(
					title = 'Saving document',
					message = 'Saving the document, please wait…',
					parent = self,
					style = wx.PD_APP_MODAL | wx.PD_ELAPSED_TIME
				)
			while True:
				try:
					queue.get(block = True, timeout = 0.1)
					break
				except QueueEmpty:
					dialog.Pulse()
		finally:
			thread.join()
			self.dirty = False
			if dialog is not None:
				dialog.Destroy()

	def on_show_sidebar(self, event):
		if event.IsChecked():
			self.do_show_sidebar()
		else:
			self.do_hide_sidebar()
	
	def do_show_sidebar(self):
		self.splitter.SplitVertically(self.sidebar, self.scrolled_panel, self.splitter._default_position)
	
	def do_hide_sidebar(self):
		self.splitter.Unsplit(self.sidebar)

	def on_display_everything(self, event):
		self.page_widget.render_mode = decode.RENDER_COLOR
	
	def on_display_foreground(self, event):
		self.page_widget.render_mode = decode.RENDER_FOREGROUND

	def on_display_background(self, event):
		self.page_widget.render_mode = decode.RENDER_BACKGROUND
	
	def on_display_stencil(self, event):
		self.page_widget.render_mode = decode.RENDER_BLACK
	
	def on_display_none(self, event):
		self.page_widget.render_mode = None
	
	def on_display_text(self, event):
		self.page_widget.render_text = event.IsChecked()
	
	def on_refresh(self, event):
		self.Refresh()

	@apply
	def page_no():
		def get(self):
			return self._page_no

		def set(self, n):
			if self.document is None:
				self._page_no = 0
				return
			if n < 0 or n >= len(self.document.pages):
				return
			self._page_no = n
			self.update_page_widget(True)
		return property(get, set)

	def on_first_page(self, event):
		self.page_no = 0

	def on_last_page(self, event):
		self.page_no = len(self.document.pages) - 1

	def on_next_page(self, event):
		self.page_no += 1

	def on_previous_page(self, event):
		self.page_no -= 1

	def on_edit_metadata(self, event):
		document_metadata_model = self.metadata_model[models.metadata.SHARED_ANNOTATIONS_PAGENO].clone()
		document_metadata_model.title = 'Document metadata'
		page_metadata_model = self.metadata_model[self.page_no].clone()
		page_metadata_model.title = 'Page %d metadata' % (self.page_no + 1)
		dialog = MetadataDialog(self, models=(document_metadata_model, page_metadata_model), known_keys=djvu.const.METADATA_KEYS)
		try:
			if dialog.ShowModal() == wx.ID_OK:
				self.metadata_model[models.metadata.SHARED_ANNOTATIONS_PAGENO] = document_metadata_model
				self.metadata_model[self.page_no] = page_metadata_model
				self.dirty = True
		finally:
			dialog.Destroy()
	
	def on_zoom(self, zoom):
		def event_handler(event):
			self.page_widget.zoom = zoom
		return event_handler
	
	def do_open(self, path):
		if self.dirty:
			dialog = wx.MessageDialog(self, 'Do you want to save your changes?', '', wx.YES_NO | wx.YES_DEFAULT | wx.CANCEL | wx.ICON_QUESTION)
			try:
				rc = dialog.ShowModal()
				if rc == wx.ID_YES:
					self.do_save()
				elif rc == wx.ID_NO:
					pass
				elif rc == wx.ID_CANCEL:
					return False
			finally:
				dialog.Destroy()
		self.path = path
		self.document = None
		self.page_no = 0
		if path is None:
			self.enable_edit(False)
		else:
			self.document = self.context.new_document(decode.FileURI(path))
			self.metadata_model = MetadataModel(self.document)
			self.enable_edit(True)
		self.update_title()
		self.update_page_widget(new_page = True)
		self.dirty = False
		return True
	
	def update_page_widget(self, new_page = False):
		if self.document is None:
			self.page = self.page_job = None
		elif self.page_job is None or new_page:
			self.page = self.document.pages[self.page_no]
			self.page_job = self.page.decode(wait = False)
		self.page_widget.page = self.page

	def update_title(self):
		if self.path is None:
			title = APPLICATION_NAME
		else:
			title = u'%s — %s' % (APPLICATION_NAME, os.path.basename(self.path))
		self.SetTitle(title)

	def on_about(self, event):
		message = '''\
%(APPLICATION_NAME)s %(__version__)s
Author: %(__author__)s
License: %(LICENSE)s''' % globals()
		wx.MessageBox(message, 'About…')
	
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

# vim:ts=4 sw=4
