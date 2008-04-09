# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>

import wx

import djvu.sexpr

class TextBrowser(wx.TreeCtrl):

	def __init__(self, parent, id = wx.ID_ANY, pos = wx.DefaultPosition, size = wx.DefaultSize, style = wx.TR_HAS_BUTTONS | wx.TR_EDIT_LABELS | wx.TR_MULTIPLE | wx.TR_HIDE_ROOT):
		wx.TreeCtrl.__init__(self, parent, id, pos, size, style)
		self._have_root = False
		self.page = None
		self.Bind(wx.EVT_TREE_BEGIN_LABEL_EDIT, self.on_begin_edit, self)
		self.Bind(wx.EVT_TREE_END_LABEL_EDIT, self.on_end_edit, self)

	@apply
	def page():
		def get(self):
			return self._page
		def set(self, value):
			self._page = value
			self._recreate_children()
		return property(get, set)

	def on_begin_edit(self, event):
		item = event.GetItem()
		if not self.do_begin_edit(item):
			event.Veto()
	
	def do_begin_edit(self, item):
		category, text, sexpr = self.GetPyData(item)
		if text is not None:
			self.SetItemText(item, text)
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
		category, old_text, sexpr = self.GetPyData(item)
		if text is None:
			text = old_text
		else:
			self.SetPyData(item, (category, text))
		sexpr[5] = text
		text = djvu.sexpr.Expression(text)
		wx.CallAfter(lambda: self.SetItemText(item, '%s %s' % (category, text)))
		return True

	def _add_children(self, item, sexprs):
		for sexpr in sexprs:
			symbol = str(sexpr[0])
			if len(sexpr) == 6 and isinstance(sexpr[5], djvu.sexpr.StringExpression):
				text = sexpr[5]
				child_item = self.AppendItem(item, '%s %s' % (symbol, sexpr[5]))
				self.SetPyData(child_item, (symbol, text.value.decode('UTF-8'), sexpr))
			else:
				child_item = self.AppendItem(item, str(sexpr[0]))
				self._add_children(child_item, sexpr[5:])
				self.SetPyData(child_item, (symbol, None, sexpr))

	def _recreate_children(self):
		root = self.GetRootItem()
		if root.IsOk():
			self.Delete(root)
		if self.page is None:
			return
		sexpr = self.page.text.sexpr
		root = self.AddRoot(str(sexpr[0].value))
		self._have_root= True
		self._add_children(root, sexpr[5:])

# vim:ts=4 sw=4
