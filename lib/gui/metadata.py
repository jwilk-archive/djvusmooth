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
import wx.grid
import wx.lib.mixins.grid

import djvu.sexpr

from djvusmooth.i18n import _

LABELS = [_('key'), _('value')]

class MetadataTable(wx.grid.PyGridTableBase):
    def __init__(self, model, known_keys):
        wx.grid.PyGridTableBase.__init__(self)
        self._model = model
        self._keys = sorted(model)
        self._keys.append(None)
        attr_normal = wx.grid.GridCellAttr()
        attr_known = wx.grid.GridCellAttr()
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        attr_known.SetFont(font)
        self._attrs = attr_normal, attr_known
        self._known_keys = known_keys

    def GetAttr(self, y, x, kind):
        key = self._keys[y]
        attr = self._attrs[x == 0 and key in self._known_keys]
        attr.IncRef()
        return attr

    def GetColLabelValue(self, n):
        return LABELS[n]

    def GetNumberRows(self):
        return len(self._keys)

    def GetNumberCols(self):
        return 2

    def GetValue(self, y, x):
        try:
            key = self._keys[y]
            if key is None:
                value = ''
            elif x:
                value = self._model[key]
            else:
                value = key
        except IndexError:
            value = ''
        return value

    def set_value(self, key, value):
        self._model[key] = value

    def set_new_key(self, y, new_key, value):
        assert isinstance(new_key, djvu.sexpr.Symbol)
        del self._model[self._keys[y]]
        self._model[new_key] = value
        self._keys[y] = new_key

    def add_new_key(self, new_key):
        assert isinstance(new_key, djvu.sexpr.Symbol)
        self._model[new_key] = ''
        y = len(self._keys) - 1
        self._keys[y:] = new_key, None
        self.GetView().ProcessTableMessage(wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED, 1))

    def delete_key(self, y):
        key = self._keys[y]
        assert isinstance(key, djvu.sexpr.Symbol)
        del self._model[key]
        del self._keys[y]
        self.GetView().ProcessTableMessage(wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED, y, 1))

    def SetValue(self, y, x, value):
        key = self._keys[y]
        if x == 0:
            if value == key:
                pass
            elif not value:
                self.delete_key(y)
                # Delete a row
            elif value in self._model:
                pass # TODO: raise an exception
            else:
                value = djvu.sexpr.Symbol(value.encode('UTF-8'))
                if key is None:
                    # Add a row
                    self.add_new_key(value)
                else:
                    self.set_new_key(y, value, self._model[key])
        elif x == 1:
            self.set_value(key, value)

class MetadataGrid(wx.grid.Grid, wx.lib.mixins.grid.GridAutoEditMixin):
    def __init__(self, parent, model, known_keys):
        wx.grid.Grid.__init__(self, parent)
        table = MetadataTable(model, known_keys)
        self.SetTable(table)
        self.SetRowLabelSize(0)
        self.SetDefaultEditor(wx.grid.GridCellAutoWrapStringEditor())
        self.AutoSize()

class MetadataDialog(wx.Dialog):

    def __init__(self, parent, models, known_keys):
        wx.Dialog.__init__(self, parent, title=_('Edit metadata'), style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        sizer = wx.BoxSizer(wx.VERTICAL)
        tabs = wx.Notebook(self, -1)
        for model in models:
            grid = MetadataGrid(tabs, model, known_keys)
            tabs.AddPage(grid, model.title)
        sizer.Add(tabs, 1, wx.EXPAND | wx.ALL, 5)
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

__all__ = 'MetadataDialog',

# vim:ts=4 sw=4 et
