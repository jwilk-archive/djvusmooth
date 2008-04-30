# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>

import wx
import wx.lib.mixins.listctrl

import models.annotations

from gui.maparea_properties import MapareaPropertiesDialog

class PageAnnotationsCallback(models.annotations.PageAnnotationsCallback):

	def __init__(self, owner):
		self.__owner = owner
	
	def notify_node_change(self, node):
		wx.CallAfter(lambda: self.__owner.on_node_change(node))
	
	def notify_node_select(self, node):
		wx.CallAfter(lambda: self.__owner.on_node_select(node))
	
	def notify_node_deselect(self, node):
		pass
	
	def notify_node_add(self, node):
		wx.CallAfter(lambda: self.__owner.on_node_add(node))
	
	def notify_node_replace(self, node, other_node):
		wx.CallAfter(lambda: self.__owner.on_node_replace(node, other_node))
	
	def notify_node_delete(self, node):
		wx.CallAfter(lambda: self.__owner.on_node_delete(node))

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
		self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.on_item_right_click, self)

	def on_node_add(self, node):
		item = self._insert_item(node)
		self.Focus(item)
	
	def on_node_replace(self, node, other_node):
		item = self._insert_item(other_node, replace_node=node)
		self.Focus(item)

	def on_node_change(self, node):
		self.on_node_replace(node, node)
	
	def on_node_select(self, node):
		try:
			current_item = self._data_map[node]
		except KeyError:
			return
		selected_item = self.GetFirstSelected()
		if selected_item != current_item:
			self.Select(selected_item, False)
			self.Select(current_item, True)
	
	def on_item_right_click(self, event):
		item = event.m_itemIndex
		node = self.GetPyData(item)
		# Yup, we accept the fact that `node` can be `None`
		self.show_menu(node, event.GetPoint())
	
	def show_menu(self, node, point):
		menu = wx.Menu()
		try:
			menu_item = menu.Append(wx.ID_ANY, u'&New hyperlink…')
			self.Bind(wx.EVT_MENU, lambda event: self.on_new_annotation(event), menu_item)
			if node is not None:
				menu_item = menu.Append(wx.ID_ANY, u'&Properties…')
				self.Bind(wx.EVT_MENU, lambda event: self.on_properties(event, node), menu_item)
			self.PopupMenu(menu, point)
		finally:
			menu.Destroy()

	def on_new_annotation(self, event):
		dialog = MapareaPropertiesDialog(self)
		try:
			if dialog.ShowModal() != wx.ID_OK:
				return
			self.page.annotations.add_maparea(dialog.node)
		finally:
			dialog.Destroy()

	def on_properties(self, event, node):
		dialog = MapareaPropertiesDialog(self, node)
		try:
			if dialog.ShowModal() != wx.ID_OK:
				return
			node.replace(dialog.node)
		finally:
			dialog.Destroy()
	
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
		id = item_to_id(item)
		return self._data.get(id)
	
	def SetPyData(self, item, data):
		id = item_to_id(item)
		try:
			del self._data_map[self._data[id]]
		except KeyError:
			pass
		self._data[id] = data
		self._data_map[data] = id
	
	def DeleteAllItem(self):
		wx.ListCtrl.DeleteAllItem(self)
		self._data.clear()
		self._data_map.clear()
	
	def _insert_item(self, node, replace_node = None):
		if replace_node in self._data_map:
			item = self._data_map[replace_node]
			i = item_to_id(item)
		else:
			i = self.GetItemCount()
			item = self.InsertStringItem(i, node.uri)
		self.SetStringItem(item, 1, node.comment, super = True)
		self.SetPyData(item, node)
		return item

	def _recreate_items(self):
		self.DeleteAllItems()
		self._nodes = []
		if self.page is None:
			return
		for node in self._model.mapareas:
			self._insert_item(node)

__all__ = 'MapAreaBrowser',

# vim:ts=4 sw=4
