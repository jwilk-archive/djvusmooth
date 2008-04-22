# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>

import wx

class MapareaPropertiesDialog(wx.Dialog):

	DEFAULT_TEXT_WIDTH = 200

	def __init__(self, parent):
		wx.Dialog.__init__(self, parent, title = 'Overprinted annotations properites')
		sizer = wx.BoxSizer(wx.VERTICAL)
		uri_box = wx.StaticBox(self, label = 'URI and target')
		uri_box_sizer = wx.StaticBoxSizer(uri_box, wx.VERTICAL)
		uri_box_gs =wx.FlexGridSizer(2, 2, 5, 5)
		uri_box_sizer.Add(uri_box_gs)
		uri_label = wx.StaticText(self, label = 'URI:')
		uri_edit = wx.TextCtrl(self, size = (self.DEFAULT_TEXT_WIDTH, -1))
		target_label = wx.StaticText(self, label = 'Target frame:')
		target_edit = wx.TextCtrl(self, size = (self.DEFAULT_TEXT_WIDTH, -1))
		for widget in uri_label, uri_edit, target_label, target_edit:
			uri_box_gs.Add(widget, 0)
		sizer.Add(uri_box_sizer, 1, wx.EXPAND | wx.ALL, 5)
		button_sizer = wx.StdDialogButtonSizer()
		button = wx.Button(self, wx.ID_OK)
		button.SetDefault()
		button_sizer.AddButton(button)
		button = wx.Button(self, wx.ID_CANCEL)
		button_sizer.AddButton(button)
		button_sizer.Realize()
		sizer.Add(button_sizer, 0, wx.EXPAND | wx.ALL, 5)
		self.SetSizerAndFit(sizer)

__all__ = 'MapareaPropertiesDialog'

# vim:ts=4 sw=4
