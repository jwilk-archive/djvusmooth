# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>

import wx

# See:
# <http://www.w3.org/TR/html4/present/frames.html#target-info>,
# <http://www.w3.org/TR/html4/types.html#type-frame-target>
# for details.

HTML_TARGETS = '_blank _self _parent _top'.split()


class MapareaPropertiesDialog(wx.Dialog):

	DEFAULT_TEXT_WIDTH = 200

	def __init__(self, parent):
		wx.Dialog.__init__(self, parent, title = 'Overprinted annotations properites')
		sizer = wx.BoxSizer(wx.VERTICAL)
		main_properties_box = wx.StaticBox(self, label = 'Main properties')
		main_properties_box_sizer = wx.StaticBoxSizer(main_properties_box)
		gs_sizer = wx.FlexGridSizer(0, 2, 5, 5)
		uri_label = wx.StaticText(self, label = 'URI:')
		uri_edit = wx.TextCtrl(self, size = (self.DEFAULT_TEXT_WIDTH, -1))
		target_label = wx.StaticText(self, label = 'Target frame:')
		target_edit = wx.ComboBox(self,
			size = (self.DEFAULT_TEXT_WIDTH, -1),
			style = wx.CB_DROPDOWN,
			choices = HTML_TARGETS
		)
		comment_label = wx.StaticText(self, label = 'Comment:')
		comment_edit = wx.TextCtrl(self, size = (self.DEFAULT_TEXT_WIDTH, -1))
		for widget in uri_label, uri_edit, target_label, target_edit, comment_label, comment_edit:
			gs_sizer.Add(widget, 0)
		main_properties_box_sizer.Add(gs_sizer, 0, wx.EXPAND | wx.ALL, 5)
		sizer.Add(main_properties_box_sizer, 0, wx.EXPAND | wx.ALL, 5)
		border_box = wx.StaticBox(self, label = 'Border')
		border_box_sizer = wx.StaticBoxSizer(border_box)
		sizer.Add(border_box_sizer, 0, wx.EXPAND | wx.ALL, 5)
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

__all__ = 'MapareaPropertiesDialog'

# vim:ts=4 sw=4
