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
import wx.lib.ogl
import wx.lib.scrolledpanel
import tempfile

from djvu import decode
import djvu.const

from djvused import StreamEditor
from gui.page import PageWidget, PercentZoom, OneToOneZoom, StretchZoom, FitWidthZoom, FitPageZoom
from gui.metadata import MetadataDialog
from gui.flatten_text import FlattenTextDialog
from gui.text_browser import TextBrowser
import text.mangle as text_mangle
import gui.dialogs
import models.metadata
import models.text
from external_editor import edit as external_edit

MENU_ICON_SIZE = (16, 16)
DJVU_WILDCARD = 'DjVu files (*.djvu, *.djv)|*.djvu;*.djv|All files|*'

wx.EVT_DJVU_MESSAGE = wx.NewId()

class WxDjVuMessage(wx.PyEvent):
	def __init__(self, message):
		wx.PyEvent.__init__(self)
		self.SetEventType(wx.EVT_DJVU_MESSAGE)
		self.message = message

class OpenDialog(wx.FileDialog):

	def __init__(self, parent):
		wx.FileDialog.__init__(self, parent, style = wx.OPEN, wildcard=DJVU_WILDCARD)

class TextModel(models.text.Text):
	def __init__(self, document):
		models.text.Text.__init__(self)
		self._document = document
	
	def acquire_metadata(self, n):
		text = self._document.pages[n].text
		text.wait()
		return text.sexpr

class PageProxy(object):
	def __init__(self, page, text_model):
		self._page = page
		self._text = text_model
	
	@property
	def page_job(self):
		return self._page.decode(wait = False)
	
	@property
	def text(self):
		return self._text

	def register_text_callback(self, callback):
		self._text.register_callback(callback)

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

class PageTextCallback(models.text.PageTextCallback):

	def __init__(self, owner):
		self._owner = owner

	def notify_node_change(self, node):
		self._owner.dirty = True
	
	def notify_node_select(self, node):
		text = '[Text layer] %s' % node.type
		if node.is_leaf():
			text += ': %s' % node.text
		self._owner.SetStatusText(text)

	def notify_node_deselect(self, node):
		self._owner.SetStatusText('')
		
	def notify_tree_change(self, node):
		self._owner.dirty = True

class MainWindow(wx.Frame):
	
	def new_menu_item(self, menu, caption, help, method, style = wx.ITEM_NORMAL, icon = None, id = wx.ID_ANY):
		item = wx.MenuItem(menu, id, caption, help, style)
		if icon is not None:
			bitmap = wx.ArtProvider_GetBitmap(icon, wx.ART_MENU, MENU_ICON_SIZE)
			item.SetBitmap(bitmap)
		self.Bind(wx.EVT_MENU, method, item)
		return item

	def __init__(self):
		wx.Frame.__init__(self, None, size=wx.Size(640, 480))
		self.Connect(wx.ID_ANY, wx.ID_ANY, wx.EVT_DJVU_MESSAGE, self.handle_message)
		self.context = Context(self)
		self._page_text_callback = PageTextCallback(self)
		self.status_bar = self.CreateStatusBar(2, style = wx.ST_SIZEGRIP)
		self.splitter = wx.SplitterWindow(self, style = wx.SP_LIVE_UPDATE)
		self.sidebar = wx.Panel(self.splitter, size = (5, 5))
		self.text_browser = TextBrowser(self.sidebar)
		sidebar_sizer = wx.BoxSizer(wx.VERTICAL)
		self.sidebar.SetSizer(sidebar_sizer)
		sidebar_sizer.Add(self.text_browser, 1, wx.ALL | wx.EXPAND)
		self.scrolled_panel = wx.lib.scrolledpanel.ScrolledPanel(self.splitter)
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
		sizer.Add(self.page_widget, 0, wx.ALL, 0)
		self.editable_menu_items = []
		self.saveable_menu_items = []
		menu_bar = wx.MenuBar()
		menu = wx.Menu()
		menu.AppendItem(self.new_menu_item(menu, '&Open\tCtrl+O', 'Open a DjVu document', self.on_open, icon=wx.ART_FILE_OPEN))
		save_menu_item = self.new_menu_item(menu, '&Save\tCtrl+S', 'Save the document', self.on_save, icon=wx.ART_FILE_SAVE)
		close_menu_item = self.new_menu_item(menu, '&Close\tCtrl+W', 'Close the document', self.on_close, id=wx.ID_CLOSE)
		menu.AppendItem(save_menu_item)
		menu.AppendItem(close_menu_item)
		self.editable_menu_items += close_menu_item,
		self.saveable_menu_items += save_menu_item,
		menu.AppendSeparator()
		menu.AppendItem(self.new_menu_item(menu, '&Quit\tCtrl+Q', 'Quit the application', self.on_exit, icon=wx.ART_QUIT))
		menu_bar.Append(menu, '&File');
		menu = wx.Menu()
		menu.AppendItem(self.new_menu_item(menu, '&Metadata\tCtrl+M', 'Edit the document or page metadata', self.on_edit_metadata))
		submenu = wx.Menu()
		submenu.AppendItem(self.new_menu_item(menu, '&External editor\tCtrl+T', 'Edit page text in an external editor', self.on_external_edit_text))
		submenu.AppendItem(self.new_menu_item(menu, '&Flatten', 'Remove details from page text', self.on_flatten_text))
		menu.AppendMenu(wx.ID_ANY, '&Text', submenu)
		menu_bar.Append(menu, '&Edit');
		menu = wx.Menu()
		submenu = wx.Menu()
		for caption, help, zoom, id in \
		[
			('Fit &width', 'Set magnification to fit page width', FitWidthZoom(), None),
			('Fit &page', 'Set magnification to fit page', FitPageZoom(), wx.ID_ZOOM_FIT),
			('&Stretch', 'Stretch the image to the window size', StretchZoom(), None),
			('One to &one', 'Set full resolution magnification.', OneToOneZoom(), wx.ID_ZOOM_100),
		]:
			submenu.AppendItem(self.new_menu_item(submenu, caption, help, self.on_zoom(zoom), style=wx.ITEM_RADIO, id = id or wx.ID_ANY))
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
		menu.AppendMenu(wx.ID_ANY, '&Zoom', submenu)

		submenu = wx.Menu()
		for caption, help, method in \
		[
			('&Color\tAlt+C', 'Display everything', self.on_display_everything),
			('&Stencil', 'Display only the document bitonal stencil', self.on_display_stencil),
			('&Foreground', 'Display only the foreground layer', self.on_display_foreground),
			('&Background', 'Display only the foreground layer', self.on_display_background),
			('&None\tAlt+N', 'Neither display the foreground layer nor the background layer', self.on_display_none)
		]:
			submenu.AppendItem(self.new_menu_item(submenu, caption, help, method, style=wx.ITEM_RADIO))
		submenu.AppendSeparator()
		submenu.AppendItem(self.new_menu_item(submenu, '&Text\tAlt+T', u'Display the text layer', self.on_display_text, style=wx.ITEM_CHECK))
		menu.AppendMenu(wx.ID_ANY, '&Display', submenu)
		menu.AppendItem(self.new_menu_item(menu, '&Refresh\tCtrl+L', 'Refresh the window', self.on_refresh))
		menu_bar.Append(menu, '&View')
		menu = wx.Menu()
		for caption, help, method, icon in \
		[
			('&First page\tCtrl-Home', 'Jump to first document page', self.on_first_page, None),
			('&Previous page\tPgUp', 'Jump to previous document page', self.on_previous_page, wx.ART_GO_UP),
			('&Next page\tPgDn', 'Jump to next document page', self.on_next_page, wx.ART_GO_DOWN),
			('&Last page\tCtrl-End', 'Jump to last document page', self.on_last_page, None),
			(u'&Go to page…', u'Jump to page…', self.on_goto_page, None)
		]:
			menu.AppendItem(self.new_menu_item(menu, caption, help, method, icon = icon))
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

	def enable_save(self, enable=True):
		for menu_item in self.saveable_menu_items:
			menu_item.Enable(enable)

	@apply
	def dirty():
		def get(self):
			return self._dirty
		def set(self, value):
			self._dirty = value
			self.enable_save(value)
		return property(get, set)

	def error_box(self, message, caption = 'Error'):
		wx.MessageBox(message = message, caption = caption, style = wx.OK | wx.ICON_ERROR, parent = self)

	def on_exit(self, event):
		if self.do_open(None):
			self.Destroy()
	
	def on_open(self, event):
		dialog = OpenDialog(self)
		try:
			if dialog.ShowModal() == wx.ID_OK:
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
		for model in self.models:
			model.export(sed)
		def job():
			try:
				sed.commit()
			except Exception, exception:
				pass
			else:
				exception = None
			queue.put(exception)
		thread = threading.Thread(target = job)
		thread.start()
		dialog = None
		try:
			try:
				queue.get(block = True, timeout = 0.1)
				return
			except QueueEmpty:
				dialog = gui.dialogs.ProgressDialog(
					title = 'Saving document',
					message = u'Saving the document, please wait…',
					parent = self,
					style = wx.PD_APP_MODAL | wx.PD_ELAPSED_TIME
				)
			while True:
				try:
					exception = queue.get(block = True, timeout = 0.1)
					if exception is not None:
						raise exception
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
				self.status_bar.SetStatusText('', 1)
				return
			if n < 0 or n >= len(self.document.pages):
				return
			self._page_no = n
			self.status_bar.SetStatusText('Page %d of %d' % ((n + 1), len(self.document.pages)), 1)
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
	
	def on_goto_page(self, event):
		dialog = gui.dialogs.NumberEntryDialog(
			parent = self,
			message = 'Go to page:',
			prompt = '',
			caption = 'Go to page',
			value = self.page_no + 1,
			min = 1,
			max = len(self.document.pages)
		)
		try:
			rc = dialog.ShowModal()
			if rc == wx.ID_OK:
				self.page_no = dialog.GetValue() - 1
		finally:
			dialog.Destroy()

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

	def on_flatten_text(self, event):
		dialog = FlattenTextDialog(self)
		zone = None
		try:
			if dialog.ShowModal() == wx.ID_OK:
				scope_all = dialog.get_scope()
				zone = dialog.get_zone()
		finally:
			dialog.Destroy()
		if zone is None:
			return
		if scope_all:
			page_nos = xrange(len(self.document.pages))
		else:
			page_nos = (self.page_no,)
		for page_no in page_nos:
			self.text_model[page_no].strip(zone)

	def on_external_edit_text(self, event):
		sexpr = self.text_model[self.page_no].raw_value
		if not len(sexpr):
			self.error_box('No text layer to edit')
			return
		def job(sexpr, dialog):
			new_sexpr = None
			try:
				tmp_file = tempfile.NamedTemporaryFile()
				try:
					text_mangle.export(sexpr, tmp_file)
					tmp_file.flush()
					external_edit(tmp_file.name)
					tmp_file.seek(0)
					try:
						new_sexpr = text_mangle.import_(sexpr, tmp_file)
					except text_mangle.NothingChanged:
						pass
				finally:
					tmp_file.close()
			except Exception, exception:
				pass
			else:
				exception = None
			wx.CallAfter(lambda: self.after_external_edit_text(new_sexpr, dialog, exception))
		disabler = wx.WindowDisabler()
		thread = threading.Thread(target = job, args = (sexpr, disabler))
		thread.start()
	
	def after_external_edit_text(self, sexpr, disabler, exception):
		if exception is not None:
			raise exception
		if sexpr is None:
			# nothing changed
			return
		self.text_model[self.page_no].raw_value = sexpr
	
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
			self.metadata_model = self.text_model = None
			self.models = ()
			self.enable_edit(False)
		else:
			self.document = self.context.new_document(decode.FileURI(path))
			self.metadata_model = MetadataModel(self.document)
			self.text_model = TextModel(self.document)
			self.models = self.metadata_model, self.text_model
			self.enable_edit(True)
		self.page_no = 0 # again, to set status bar text
		self.update_title()
		self.update_page_widget(new_page = True)
		self.dirty = False
		return True
	
	def update_page_widget(self, new_page = False):
		if self.document is None:
			self.page = self.page_job = self.page_proxy = None
		elif self.page_job is None or new_page:
			self.page = self.document.pages[self.page_no]
			self.page_job = self.page.decode(wait = False)
			self.page_proxy = PageProxy(
				page = self.page,
				text_model = self.text_model[self.page_no])
			self.page_proxy.register_text_callback(self._page_text_callback)
		self.page_widget.page = self.page_proxy
		self.text_browser.page = self.page_proxy

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
		wx.MessageBox(message, u'About…')
	
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
		wx.lib.ogl.OGLInitialize()
		window = MainWindow()
		window.Show(True)
		if self._argv:
			window.do_open(self._argv.pop(0))
		return True

def main(argv):
	app = SmoothApp(argv)
	app.MainLoop()

# vim:ts=4 sw=4
