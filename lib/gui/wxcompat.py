# encoding=UTF-8

# Copyright © 2014-2015 Jakub Wilk <jwilk@jwilk.net>
#
# This package is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 dated June, 1991.
#
# This package is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

'''
work-arounds for wxPython 3.0 quirks
'''

import wx

# In wxPython 3.0, if the focus is on a wxTreeCtrl or a wxListCtrl, menu
# events for at last Page Up, Page Down, Ctrl+Home and Ctrl+End are getting
# lost. This module implements wxEVT_KEY_DOWN handler to work-around this
# problem.
#
# https://bugs.debian.org/758950#26

def iter_menu(menu):
    for item in menu.MenuItems:
        submenu = item.SubMenu
        if submenu is None:
            yield item
        else:
            for item in iter_menu(submenu):
                yield item

def on_key_down(ctrl, event):
    window = wx.GetTopLevelParent(ctrl)
    menubar = window.MenuBar
    for menu, label in menubar.Menus:
        for item in iter_menu(menu):
            if item.Accel is None:
                continue
            if item.Accel.Flags != event.Modifiers:
                continue
            if item.Accel.KeyCode != event.KeyCode:
                continue
            break
        else:
            item = None
        if item is not None:
            break
    if item is None:
        event.Skip()
    else:
        evt = wx.CommandEvent(wx.EVT_MENU.typeId, item.Id)
        evt.SetEventObject(window)
        wx.PostEvent(window, evt)

if wx.VERSION < (3, 0):
    del on_key_down  # quieten pyflakes
    def on_key_down(ctrl, event):
        event.Skip()

# vim:ts=4 sts=4 sw=4 et
