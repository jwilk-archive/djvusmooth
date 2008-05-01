# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>

import wx

from gui.maparea_properties import MapareaPropertiesDialog

def show_menu(parent, annotations, node, point, origin=None):
	menu = wx.Menu()
	try:
		menu_item = menu.Append(wx.ID_ANY, u'&New hyperlink…')
		parent.Bind(wx.EVT_MENU, lambda event: on_new_annotation(event, parent, annotations, origin), menu_item)
		if node is not None:
			menu_item = menu.Append(wx.ID_ANY, u'&Properties…')
			parent.Bind(wx.EVT_MENU, lambda event: on_properties(event, parent, node), menu_item)
		parent.PopupMenu(menu, point)
	finally:
		menu.Destroy()
	
def on_new_annotation(event, parent, annotations, origin):
	dialog = MapareaPropertiesDialog(parent, origin=origin)
	try:
		if dialog.ShowModal() != wx.ID_OK:
			return
		annotations.add_maparea(dialog.node)
	finally:
		dialog.Destroy()

def on_properties(event, parent, node):
	dialog = MapareaPropertiesDialog(parent, node)
	try:
		if dialog.ShowModal() != wx.ID_OK:
			return
		node.replace(dialog.node)
	finally:
		dialog.Destroy()

# vim:ts=4 sw=4
