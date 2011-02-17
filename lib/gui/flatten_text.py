# encoding=UTF-8
# Copyright © 2008, 2009 Jakub Wilk <jwilk@jwilk.net>
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

import djvu.sexpr
import djvu.const

from djvusmooth.i18n import _

ZONES_MAP = \
(
    (_('all'),        djvu.const.TEXT_ZONE_PAGE),
    (_('columns'),    djvu.const.TEXT_ZONE_COLUMN),
    (_('regions'),    djvu.const.TEXT_ZONE_REGION),
    (_('paragraphs'), djvu.const.TEXT_ZONE_PARAGRAPH),
    (_('lines'),      djvu.const.TEXT_ZONE_LINE),
    (_('words'),      djvu.const.TEXT_ZONE_WORD),
    (_('characters'), djvu.const.TEXT_ZONE_CHARACTER)
)

class FlattenTextDialog(wx.Dialog):

    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, title = _('Flatten text'))
        sizer = wx.BoxSizer(wx.VERTICAL)
        self._scope_box = wx.RadioBox(self,
            label = _('Scope') + ':',
            choices = (_('current page'), _('all pages')),
            style = wx.RA_HORIZONTAL
        )
        self._zone_box = wx.RadioBox(self,
            label = _('Remove details') + ':',
            choices = [label for label, type in ZONES_MAP],
            style = wx.RA_SPECIFY_COLS, majorDimension = 2
        )
        self._zone_box.SetSelection(len(ZONES_MAP) - 1)
        for box in self._scope_box, self._zone_box:
            sizer.Add(box, 0, wx.EXPAND | wx.ALL, 5)
        line = wx.StaticLine(self, -1, style = wx.LI_HORIZONTAL)
        sizer.Add(line, 0, wx.EXPAND | wx.BOTTOM | wx.TOP, 5)
        button_sizer = wx.StdDialogButtonSizer()
        button = wx.Button(self, wx.ID_OK)
        button.SetDefault()
        button_sizer.AddButton(button)
        button = wx.Button(self, wx.ID_CANCEL)
        button_sizer.AddButton(button)
        button_sizer.Realize()
        sizer.Add(button_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.SetSizerAndFit(sizer)

    def get_scope(self):
        return self._scope_box.GetSelection()

    def get_zone(self):
        label, zone = ZONES_MAP[self._zone_box.GetSelection()]
        return zone

__all__ = 'FlattenTextDialog',

# vim:ts=4 sw=4 et
