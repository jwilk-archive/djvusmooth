# encoding=UTF-8

# Copyright © 2012 Jakub Wilk <jwilk@jwilk.net>
#
# This package is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 dated June, 1991.
#
# This package is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

import itertools

import wx

class FileHistory(object):

    def __init__(self, config):
        self._wx = wx.FileHistory()
        self._config = config
        to_add = []
        for i in itertools.count(0):
            key = 'recent[{0}]'.format(i)
            path = config.read(key, None)
            if path is None:
                break
            to_add += [path]
        for path in reversed(to_add):
            self._add(path)

    def _add(self, path):
        self._wx.AddFileToHistory(path)

    def add(self, path):
        self._add(path)
        config = self._config
        config.del_array('recent')
        for n, path in enumerate(self):
            config['recent[{0}]'.format(n)] = path
        self._enable_menu_item()

    def set_menu(self, window, menu_item, on_click):
        menu = menu_item.GetSubMenu()
        self._wx.UseMenu(menu)
        self._wx.AddFilesToMenu()
        self._menu_item = menu_item
        id1 = wx.ID_FILE1
        id2 = id1 + self._get_max_length()
        def on_click_wrapper(event):
            n = event.GetId() - wx.ID_FILE1
            path = self[n]
            return on_click(path)
        window.Bind(wx.EVT_MENU_RANGE, on_click_wrapper, id=id1, id2=id2)
        self._enable_menu_item()

    def _enable_menu_item(self):
        self._menu_item.Enable(enable=bool(self))

    def __len__(self):
        return self._wx.Count

    def __iter__(self):
        return (
            self[n]
            for n in xrange(len(self))
        )

    def __getitem__(self, n):
        return self._wx.GetHistoryFile(n)

    def _get_max_length(self):
        return self._wx.GetMaxFiles()

# vim:ts=4 sts=4 sw=4 et
