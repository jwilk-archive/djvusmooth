# encoding=UTF-8
# Copyright © 2014 Jakub Wilk <jwilk@jwilk.net>
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
    def on_key_down(ctrl, event):
        event.Skip()

# vim:ts=4 sw=4 et
