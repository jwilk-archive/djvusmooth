# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>

import wx

class ProgressDialog(wx.ProgressDialog):

	def __init__(self, title, message, maximum = 100, parent = None, style = wx.PD_AUTO_HIDE | wx.PD_APP_MODAL):
		wx.ProgressDialog.__init__(self, title, message, maximum, parent, style)
		self.__max = maximum
		self.__n = 0
		
	try:
		wx.ProgressDialog.Pulse
	except AttributeError:
		def Pulse(self):
			self.__n = (self.__n + 1) % self.__max
			self.Update(self.__n)

try:
	NumberEntryDialog = wx.NumberEntryDialog
except AttributeError:
	class NumberEntryDialog(wx.SingleChoiceDialog):
		def __init__(self, parent, message, prompt, caption, value, min, max, pos = wx.DefaultPosition):
			wx.SingleChoiceDialog.__init__(self, parent = parent, message = message, caption = caption, choices = map(str, xrange(min, max + 1)), pos = pos)
			self.SetSelection(value - min)

		def GetValue(self):
			return int(wx.SingleChoiceDialog.GetStringSelection(self))

# vim:ts=4 sw=4
