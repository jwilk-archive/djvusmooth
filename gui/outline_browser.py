# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>

import re
import wx

import djvu.sexpr

import models.outline

replace_control_characters = re.compile('[\0-\x1f]+').sub

def get_label_for_node(node):
	return replace_control_characters(' ', node.text)

class OutlineCallback(models.outline.OutlineCallback):

	def __init__(self, browser):
		self._browser = browser
	
	def notify_node_change(self, node):
		wx.CallAfter(lambda: self._browser.on_node_change(node))
	
	def notify_node_select(self, node):
		pass

	def notify_tree_change(self, node):
		wx.CallAfter(lambda: self._browser.on_tree_change(node))
	
class OutlineBrowser(wx.TreeCtrl):

	def __init__(self, parent, id = wx.ID_ANY, pos = wx.DefaultPosition, size = wx.DefaultSize, style = wx.TR_HAS_BUTTONS | wx.TR_EDIT_LABELS | wx.TR_HIDE_ROOT):
		wx.TreeCtrl.__init__(self, parent, id, pos, size, style)
		self._have_root = False
		self._document = None
		self.Bind(wx.EVT_TREE_BEGIN_LABEL_EDIT, self.on_begin_edit, self)
		self.Bind(wx.EVT_TREE_END_LABEL_EDIT, self.on_end_edit, self)
		self.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_selection_changed, self)
		self.Bind(wx.EVT_CHAR, self.on_char)

	def on_char(self, event):
		key_code = event.GetKeyCode()
		if key_code == wx.WXK_RETURN:
			item = self.GetSelection()
			node = self.GetPyData(item)
			uri = node.uri
			if uri.startswith('#'):
				try:
					n = int(buffer(uri, 1))
				except ValueError:
					pass # TODO: try to handle non-local URIs
				parent = wx.GetTopLevelParent(self)
				parent.page_no = n - 1
			else:
				pass # TODO: try to handle non-local URIs

	def on_node_change(self, node):
		try:
			item = self._items[node]
		except KeyError:
			return
		self.SetItemText(item, get_label_for_node(node))

	def on_tree_change(self, model_node):
		self.document = True

	@apply
	def document():
		def get(self):
			return self._document
		def set(self, value):
			if value is not True:
				self._document = value
			if self._document is not None:
				self._callback = OutlineCallback(self)
				self._document.outline.register_callback(self._callback)
			self._recreate_children()
		return property(get, set)

	def on_selection_changed(self, event):
		item = event.GetItem()
		if item:
			node = self.GetPyData(item)
			node.notify_select()
		event.Skip()

	def on_begin_edit(self, event):
		item = event.GetItem()
		if not self.do_begin_edit(item):
			event.Veto()
	
	def do_begin_edit(self, item):
		node = self.GetPyData(item)
		self.SetItemText(item, node.text)
		return True
	
	def on_end_edit(self, event):
		item = event.GetItem()
		if event.IsEditCancelled():
			new_text = None
		else:
			new_text = event.GetLabel()
		if not self.do_end_edit(item, new_text):
			event.Veto()
	
	def do_end_edit(self, item, text):
		node = self.GetPyData(item)
		if text is None:
			text = node.text
		node.text = text
		return True

	def _add_children(self, item, nodes):
		for node in nodes:
			symbol = node.type
			label = get_label_for_node(node)
			child_item = self.AppendItem(item, label)
			self._add_children(child_item, node)
			self._items[node] = child_item
			self.SetPyData(child_item, node)

	def _recreate_children(self):
		self._items = {}
		root = self.GetRootItem()
		if root.IsOk():
			self.Delete(root)
		if self.document is None:
			return
		node = self.document.outline.root
		if node:
			root = self.AddRoot(str(node.type))
			self._have_root = True
			self._add_children(root, node)

__all__ = 'OutlineBrowser',

# vim:ts=4 sw=4
