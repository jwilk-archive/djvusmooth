# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>

import wx
import wx.lib.mixins.listctrl

import models.annotations

class PageAnnotationsCallback(models.annotations.PageAnnotationsCallback):

	def __init__(self, owner):
		self.__owner = owner
	
	def notify_node_change(self, node):
		wx.CallAfter(lambda: self.__owner.on_node_change(node))
	
	def notify_node_select(self, node):
		wx.CallAfter(lambda: self.__owner.on_node_select(node))
	
	def notify_node_deselect(self, node):
		pass

def item_to_id(item):
	try:
		return int(item)
	except TypeError:
		return item.GetId()

class MapAreaBrowser(
	wx.ListCtrl,
	wx.lib.mixins.listctrl.ListCtrlAutoWidthMixin,
	wx.lib.mixins.listctrl.TextEditMixin
):

	def __init__(self, parent, id = wx.ID_ANY, pos = wx.DefaultPosition, size = wx.DefaultSize, style = wx.LC_REPORT):
		wx.ListCtrl.__init__(self, parent, id, pos, size, style)
		self.InsertColumn(0, 'URI')
		self.InsertColumn(1, 'Comment')
		self._have_items = False
		self._data = {}
		self._data_map = {}
		self.page = None
		wx.lib.mixins.listctrl.ListCtrlAutoWidthMixin.__init__(self)
		wx.lib.mixins.listctrl.TextEditMixin.__init__(self)
		self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_selection_changed, self)
	
	def on_node_change(self, node):
		# TODO
		pass
	
	def on_node_select(self, node):
		try:
			current_item = self._data_map[node]
		except KeyError:
			return
		selected_item = self.GetFirstSelected()
		if selected_item != current_item:
			self.Select(selected_item, False)
			self.Select(current_item, True)
	
	def on_selection_changed(self, event):
		event.Skip()
		item = event.m_itemIndex
		node = self.GetPyData(item)
		if node is None:
			return
		node.notify_select()
	
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

	def SetStringItem(self, item, col, label, super = False):
		wx.ListCtrl.SetStringItem(self, item, col, label)
		if super:
			return
		node = self.GetPyData(item)
		if node is None:
			return
		if col == 0:
			node.uri = label
		elif col == 1:
			node.comment = label


	def GetPyData(self, item):
		return self._data.get(item_to_id(item))
	
	def SetPyData(self, item, data):
		id = item_to_id(item)
		self._data[item] = data
		self._data_map[data] = item
	
	def DeleteAllItem(self):
		wx.ListCtrl.DeleteAllItem(self)
		self._data.clear()
		self._data_map.clear()

	def _recreate_items(self):
		self.DeleteAllItems()
		self._nodes = []
		if self.page is None:
			return
		for i, node in enumerate(self._model.mapareas):
			item = self.InsertStringItem(i, node.uri)
			self.SetStringItem(item, 1, node.comment, super = True)
			self.SetPyData(item, node)

__all__ = 'MapAreaBrowser',

# vim:ts=4 sw=4
