# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>

import wx

import djvu.sexpr
import djvu.const

ZONES_MAP = \
(
	('all',        djvu.const.TEXT_ZONE_PAGE),
	('columns',    djvu.const.TEXT_ZONE_COLUMN),
	('regions',    djvu.const.TEXT_ZONE_REGION),
	('paragraphs', djvu.const.TEXT_ZONE_PARAGRAPH),
	('lines',      djvu.const.TEXT_ZONE_LINE),
	('words',      djvu.const.TEXT_ZONE_WORD),
	('characters', djvu.const.TEXT_ZONE_CHARACTER)
)

class FlattenTextDialog(wx.Dialog):

	def __init__(self, parent):
		wx.Dialog.__init__(self, parent, title = 'Flatten text')
		sizer = wx.BoxSizer(wx.VERTICAL)
		self._scope_box = wx.RadioBox(self,
			label = 'Scope:',
			choices = ('current page', 'all pages'),
			style = wx.RA_HORIZONTAL
		)
		self._zone_box = wx.RadioBox(self,
			label = 'Remove details:',
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

# vim:ts=4 sw=4
