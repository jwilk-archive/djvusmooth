# encoding=UTF-8
# Copyright © 2008, 2009, 2010 Jakub Wilk <jwilk@jwilk.net>
# Copyright © 2009 Mateusz Turcza <mturcza@mimuw.edu.pl>
#
# This package is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 dated June, 1991.
#
# This package is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

import wx

import djvusmooth.models.text
from djvusmooth import models
from djvusmooth.varietes import replace_control_characters
from djvusmooth.i18n import _

def get_label_for_node(node):
    zone_type = str(node.type)
    if node.is_inner():
        return _(zone_type)
    else:
        return _(zone_type) + ': ' + replace_control_characters(' ', node.text)

class PageTextCallback(models.text.PageTextCallback):

    def __init__(self, browser):
        self._browser = browser

    def notify_node_change(self, node):
        wx.CallAfter(lambda: self._browser.on_node_change(node))

    def notify_node_children_change(self, node):
        wx.CallAfter(lambda: self._browser.on_tree_change(node))
        # FIXME: consider something lighter here

    def notify_tree_change(self, node):
        wx.CallAfter(lambda: self._browser.on_tree_change(node))

    def notify_node_deselect(self, node): pass

    def notify_node_select(self, node):
        wx.CallAfter(lambda: self._browser.on_node_select(node))

class TextBrowser(wx.TreeCtrl):

    def __init__(self, parent, id = wx.ID_ANY, pos = wx.DefaultPosition, size = wx.DefaultSize, style = wx.TR_HAS_BUTTONS | wx.TR_EDIT_LABELS):
        wx.TreeCtrl.__init__(self, parent, id, pos, size, style)
        self._have_root = False
        self.page = None
        self.Bind(wx.EVT_TREE_BEGIN_LABEL_EDIT, self.on_begin_edit, self)
        self.Bind(wx.EVT_TREE_END_LABEL_EDIT, self.on_end_edit, self)
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_selection_changed, self)

    def on_node_change(self, node):
        try:
            item = self._items[node]
        except KeyError:
            return
        if node.is_inner():
            return
        self.SetItemText(item, get_label_for_node(node))

    def on_node_select(self, node):
        try:
            item = self._items[node]
        except KeyError:
            return
        if self.GetSelection() != item:
            self.SelectItem(item)

    def on_tree_change(self, model_node):
        self.page = True

    @apply
    def page():
        def get(self):
            return self._page
        def set(self, value):
            if value is not True:
                self._page = value
            if self._page is not None:
                self._callback = PageTextCallback(self)
                self._page.text.register_callback(self._callback)
            self._recreate_children()
        return property(get, set)

    def on_selection_changed(self, event):
        event.Skip()
        item = event.GetItem()
        if not item:
            return
        node = self.GetPyData(item)
        if node is None:
            return
        node.notify_select()

    def on_begin_edit(self, event):
        item = event.GetItem()
        if not self.do_begin_edit(item):
            event.Veto()

    def do_begin_edit(self, item):
        node = self.GetPyData(item)
        if node is None:
            return
        if node.is_leaf():
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
        if node is None:
            return
        if text is None:
            text = node.text
        node.text = text
        return True

    def _add_children(self, item, parent_node):
        if not parent_node.is_inner():
            return
        for node in parent_node:
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
        if self.page is None:
            return
        node = self.page.text.root
        if node is not None:
            label = get_label_for_node(node)
            root = self.AddRoot(label)
            self._items[node] = root
            self.SetPyData(root, node)
            self._have_root = True
            self._add_children(root, node)

__all__ = 'TextBrowser',

# vim:ts=4 sw=4 et
