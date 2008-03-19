#!/usr/bin/python
# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>

import wx
import wx.grid
import wx.lib.mixins.grid

LABELS = 'key value'.split()

class MetadataTable(wx.grid.PyGridTableBase):
	def __init__(self, model):
		wx.grid.PyGridTableBase.__init__(self)
		self._model = model
		self._keys = sorted(model)

	def GetColLabelValue(self, n):
		return LABELS[n]
	
	def GetNumberRows(self):
		return len(self._keys)

	def GetNumberCols(self):
		return 2

	def GetValue(self, y, x):
		key = self._keys[y]
		if x:
			value = self._model[key]
		else:
			value = key
		return value

	def set_value(self, key, value):
		self._model[key] = value
	
	def set_new_key(self, y, new_key, value):
		del self._model[self._keys[y]]
		self._model[new_key] = value
		self._keys[y] = new_key

	def SetValue(self, y, x, value):
		key = self._keys[y]
		if x == 0:
			if value == key:
				pass
			elif value in self._model:
				pass # TODO: raise an exception
			else:
				self.set_new_key(y, value, self._model[key])
		elif x == 1:
			self.set_value(key, value)

class MetadataGrid(wx.grid.Grid, wx.lib.mixins.grid.GridAutoEditMixin):
	def __init__(self, parent, model):
		wx.grid.Grid.__init__(self, parent, size=(480, 360))
		table = MetadataTable(model)
		self.SetTable(table)
		self.SetRowLabelSize(0)
		self.SetDefaultEditor(wx.grid.GridCellAutoWrapStringEditor())
		self.AutoSize()

class MetadataDialog(wx.Dialog):

	def __init__(self, parent, model):
		wx.Dialog.__init__(self, parent, title='Edit metadata', style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
		self._model = model
		sizer = wx.BoxSizer(wx.VERTICAL)
		grid = MetadataGrid(self, model)
		sizer.Add(grid, 1, wx.EXPAND | wx.ALL, 5)
		line = wx.StaticLine(self, -1, style = wx.LI_HORIZONTAL)
		sizer.Add(line, 0, wx.GROW | wx.ALIGN_CENTER_VERTICAL | wx.RIGHT | wx.TOP, 5)
		button_sizer = wx.StdDialogButtonSizer()
		button = wx.Button(self, wx.ID_OK)
		button.SetDefault()
		button_sizer.AddButton(button)
		button = wx.Button(self, wx.ID_CANCEL)
		button_sizer.AddButton(button)
		button_sizer.Realize()
		sizer.Add(button_sizer, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
		self.SetSizer(sizer)
		sizer.Fit(self)

# vim:ts=4 sw=4
