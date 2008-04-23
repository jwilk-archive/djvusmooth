# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>

import wx

import models.annotations

class PageAnnotationsCallback(models.annotations.PageAnnotationsCallback):

	def __init__(self, owner):
		self.__owner = owner

class MapAreaBrowser(wx.ListCtrl):

	def __init__(self, parent, id = wx.ID_ANY, pos = wx.DefaultPosition, size = wx.DefaultSize, style = wx.LC_ICON):
		wx.ListCtrl.__init__(self, parent, id, pos, size, style)
		self._have_items = False
		self.page = None

	@apply
	def page():
		def get(self):
			return self._page
		def set(self, value):
			if value is not True:
				self._page = value
			if self._page is not None:
				self._callback = PageAnnotationsCallback(self)
				self._page.annotations.register_callback(self._callback)
				self._model = self.page.annotations
			self._recreate_items()
		return property(get, set)
	
	def _recreate_items(self):
		self.DeleteAllItems()
		if self.page is None:
			return
		for item in self._model.mapareas:
			self.InsertStringItem(0, '<map area>')

__all__ = 'MapAreaBrowser',

# vim:ts=4 sw=4
