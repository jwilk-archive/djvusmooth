# encoding=UTF-8

# Copyright © 2008-2009 Jakub Wilk <jwilk@jwilk.net>
# Copyright © 2009 Mateusz Turcza <mturcza@mimuw.edu.pl>
#
# This file is part of djvusmooth.
#
# djvusmooth is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# djvusmooth is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
# more details.

import wx

from djvusmooth.gui.maparea_properties import MapareaPropertiesDialog
from djvusmooth.i18n import _

def show_menu(parent, annotations, node, point, origin=None):
    menu = wx.Menu()
    try:
        menu_item = menu.Append(wx.ID_ANY, _(u'&New hyperlink…'))
        parent.Bind(wx.EVT_MENU, lambda event: on_new_annotation(event, parent, annotations, origin), menu_item)
        if node is not None:
            menu_item = menu.Append(wx.ID_ANY, _(u'&Properties…'))
            parent.Bind(wx.EVT_MENU, lambda event: on_properties(event, parent, node), menu_item)
            menu_item = menu.Append(wx.ID_ANY, _('&Remove') + '\tDel')
            parent.Bind(wx.EVT_MENU, lambda event: on_delete(event, parent, node), menu_item)
        del menu_item
        parent.PopupMenu(menu, point)
    finally:
        menu.Destroy()

def on_new_annotation(event, parent, annotations, origin):
    dialog = MapareaPropertiesDialog(parent, origin=origin)
    try:
        if dialog.ShowModal() != wx.ID_OK:
            return
        dialog.node.insert(annotations)
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

def on_delete(event, parent, node):
    node.delete()

# vim:ts=4 sts=4 sw=4 et
