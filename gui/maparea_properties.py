# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>

import wx
import wx.lib.colourselect

import djvu.const

import models.annotations
from varietes import idict

# See:
# <http://www.w3.org/TR/html4/present/frames.html#target-info>,
# <http://www.w3.org/TR/html4/types.html#type-frame-target>
# for details.

HTML_TARGETS = '_blank _self _parent _top'.split()

class Shape(idict):
	def __init__(self, **kwargs):
		kwargs.setdefault('enabled', True)
		idict.__init__(self, **kwargs)

SHAPE_TEXT = Shape(label = 'Text', symbol = djvu.const.MAPAREA_SHAPE_TEXT)
SHAPE_LINE = Shape(label = 'Line', symbol = djvu.const.MAPAREA_SHAPE_LINE)
SHAPE_RECTANGLE = Shape(label = 'Rectangle', symbol = djvu.const.MAPAREA_SHAPE_RECTANGLE)
SHAPES = (
	SHAPE_RECTANGLE,
	Shape(label = 'Oval', symbol = djvu.const.MAPAREA_SHAPE_OVAL),
	Shape(label = 'Polygon', symbol = djvu.const.MAPAREA_SHAPE_POLYGON, enabled = False),
	SHAPE_LINE,
	SHAPE_TEXT,
)

SHADOW_BORDERS = (
	idict(model_class = models.annotations.BorderShadowIn,  label = 'Shadow in'),
	idict(model_class = models.annotations.BorderShadowOut, label = 'Shadow out'),
	idict(model_class = models.annotations.BorderEtchedIn,  label = 'Etched in'),
	idict(model_class = models.annotations.BorderEtchedOut, label = 'Etched out')
)

class MapareaPropertiesDialog(wx.Dialog):

	DEFAULT_TEXT_WIDTH = 200

	def _setup_main_properties_box(self):
		node = self._node
		box = wx.StaticBox(self, label = 'Main properties')
		box_sizer = wx.StaticBoxSizer(box)
		grid_sizer = wx.FlexGridSizer(0, 2, 5, 5)
		uri_label = wx.StaticText(self, label = 'URI: ')
		uri_edit = wx.TextCtrl(self, size = (self.DEFAULT_TEXT_WIDTH, -1))
		if node is not None:
			uri_edit.SetValue(self._node.uri)
		target_label = wx.StaticText(self, label = 'Target frame: ')
		target_edit = wx.ComboBox(self,
			size = (self.DEFAULT_TEXT_WIDTH, -1),
			style = wx.CB_DROPDOWN,
			choices = HTML_TARGETS
		)
		if node is not None:
			target_edit.SetValue(self._node.target or '')
		comment_label = wx.StaticText(self, label = 'Comment: ')
		comment_edit = wx.TextCtrl(self, size = (self.DEFAULT_TEXT_WIDTH, -1))
		if node is not None:
			comment_edit.SetValue(self._node.comment)
		for widget in uri_label, uri_edit, target_label, target_edit, comment_label, comment_edit:
			grid_sizer.Add(widget)
		box_sizer.Add(grid_sizer, 0, wx.EXPAND | wx.ALL, 5)
		self._edit_uri = uri_edit
		self._edit_target = target_edit
		self._edit_comment = comment_edit
		return box_sizer

	def _setup_shape_box(self):
		box = wx.RadioBox(self,
			label = 'Shape',
			choices = [shape.label for shape in SHAPES]
		)
		for i, shape in enumerate(SHAPES):
			box.EnableItem(i, shape.enabled)
		self.Bind(wx.EVT_RADIOBOX, self.on_select_shape, box)
		self._edit_shape = box
		# It's too early to select proper shape. We'll do it later.
		return box

	def do_select_shape(self, shape):
		for _shape, items in self._specific_sizers.iteritems():
			for item in items:
				self._sizer.Show(item, False, recursive=True)
		try:
			specific_sizers = self._specific_sizers[shape]
		except KeyError:
			pass
		else:
			for item in specific_sizers:
				self._sizer.Show(item, True, recursive=True)
		self.Fit()

	def on_select_shape(self, event):
		shape = SHAPES[event.GetInt()]
		self.do_select_shape(shape)

	def _setup_border_box(self):
		node = self._node
		try:
			border = node.border
		except AttributeError:
			border = None
		box = wx.StaticBox(self, label = 'Border')
		box_sizer = wx.StaticBoxSizer(box, orient = wx.VERTICAL)
		box_grid_sizer = wx.GridSizer(0, 3)
		radio_none = wx.RadioButton(self, label = 'None')
		radio_xor = wx.RadioButton(self, label = 'XOR')
		if isinstance(border, models.annotations.XorBorder):
			radio_xor.SetValue(True)
		radio_solid = wx.RadioButton(self, label = 'Solid color')
		solid_color_selector = wx.lib.colourselect.ColourSelect(self, wx.ID_ANY)
		if isinstance(border, models.annotations.SolidBorder):
			radio_solid.SetValue(True)
			solid_color_selector.SetColour(border.color)
		solid_sizer = wx.BoxSizer(wx.HORIZONTAL)
		solid_sizer.Add(radio_solid, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
		solid_sizer.Add(solid_color_selector, 0, wx.ALIGN_CENTER_VERTICAL)
		for widget in radio_none, radio_xor, solid_sizer:
			box_grid_sizer.Add(widget, 0, wx.ALIGN_CENTER_VERTICAL)
		shadow_widgets = []
		for i, shadow_border in enumerate(SHADOW_BORDERS):
			if i and (i & 1 == 0):
				box_grid_sizer.Add((0, 0))
			widget = wx.RadioButton(self, label = shadow_border.label)
			if isinstance(border, shadow_border.model_class):
				widget.SetValue(True)
			widget.model_class = shadow_border.model_class
			box_grid_sizer.Add(widget, 0, wx.ALIGN_CENTER_VERTICAL)
			shadow_widgets += widget,
		avis_checkbox = wx.CheckBox(self, label = 'Always visible') # TODO: hide it for irrelevant shapes, i.e. `line` and maybe `text`
		if node.border_always_visible is True:
			avis_checkbox.SetValue(True)
		box_sizer.Add(box_grid_sizer, 0, wx.EXPAND | wx.ALL, 5)
		box_sizer.Add(avis_checkbox, 0, wx.ALL, 5)
		self._edit_border_none = radio_none
		self._edit_border_xor = radio_xor
		self._edit_border_solid = radio_solid
		self._edit_border_solid_color = solid_color_selector
		self._edit_border_shadows = shadow_widgets
		self._edit_border_always_visible = True
		return box_sizer
	
	def _setup_extra_boxes(self):
		node = self._node
		extra_boxes = \
		[
			wx.StaticBox(self, label = label)
			for label in ('Highlight color and opacity', 'Line-specific properties', 'Text-specific properties')
		]
		extra_sizers = map(wx.StaticBoxSizer, extra_boxes)
		highlight_specific_sizer, line_specific_sizer, text_specific_sizer = extra_sizers
		self._specific_sizers = {
			SHAPE_RECTANGLE: [highlight_specific_sizer],
			SHAPE_LINE: [line_specific_sizer],
			SHAPE_TEXT: [text_specific_sizer]
		}
		extra_grid_sizers = [wx.FlexGridSizer(0, 2, 5, 5) for i in extra_sizers]
		for extra_sizer, extra_grid_sizer in zip(extra_sizers, extra_grid_sizers):
			extra_sizer.Add(extra_grid_sizer, 0, wx.EXPAND | wx.ALL, 5)
		highlight_specific_sizer, line_specific_sizer, text_specific_sizer = extra_grid_sizers
		highlight_color_label = wx.CheckBox(self, label = 'Highlight color: ')
		highlight_color_selector = wx.lib.colourselect.ColourSelect(self, wx.ID_ANY) # TODO: hide if label not checked
		opacity_label = wx.StaticText(self, label = 'Opacity: ')
		opacity_slider = wx.Slider(self,
			value = 50,
			size = (self.DEFAULT_TEXT_WIDTH, -1),
			style = wx.SL_HORIZONTAL | wx.SL_AUTOTICKS | wx.SL_LABELS
		)
		for widget in highlight_color_label, highlight_color_selector, opacity_label, opacity_slider:
			highlight_specific_sizer.Add(widget, 0, wx.ALIGN_CENTER_VERTICAL)
		if isinstance(node, models.annotations.RectangleMapArea):
			if node.highlight_color is None:
				highlight_color_label.SetValue(False)
			else:
				highlight_color_label.SetValue(True)
				highlight_color_selector.SetColour(node.highlight_color)
			opacity_slider.SetValue(node.opacity)
		line_width_label = wx.StaticText(self, label = 'Line width: ')
		line_width_edit = wx.SpinCtrl(self)
		line_width_edit.SetRange(1, 999)
		line_color_label = wx.StaticText(self, label = 'Line color: ')
		line_color_selector = wx.lib.colourselect.ColourSelect(self, wx.ID_ANY)
		line_arrow_checkbox = wx.CheckBox(self, label = 'Arrow')
		dummy = (0, 0)
		for widget in line_arrow_checkbox, dummy, line_width_label, line_width_edit, line_color_label, line_color_selector:
			line_specific_sizer.Add(widget, 0, wx.ALIGN_CENTER_VERTICAL)
		if isinstance(node, models.annotations.LineMapArea):
			line_width_edit.SetValue(node.line_width)
			line_color_selector.SetColour(node.line_color)
			line_arrow_checkbox.SetValue(node.line_arrow)
		text_background_color_label = wx.CheckBox(self, label = 'Background color: ')
		text_background_color_selector = wx.lib.colourselect.ColourSelect(self, wx.ID_ANY) # TODO: hide if label not checked
		text_color_label = wx.StaticText(self, label = 'Text color: ')
		text_color_selector = wx.lib.colourselect.ColourSelect(self, wx.ID_ANY)
		text_pushpin = wx.CheckBox(self, label = 'Pushpin')
		for widget in text_background_color_label, text_background_color_selector, text_color_label, text_color_selector, text_pushpin:
			text_specific_sizer.Add(widget, 0, wx.ALIGN_CENTER_VERTICAL)
		if isinstance(node, models.annotations.TextMapArea):
			if node.background_color is not None:
				text_background_color_label.SetValue(True)
				text_background_color_selector.SetColour(node.background_color)
			else:
				text_background_color_label.SetValue(False)
			text_color_selector.SetColour(node.text_color)
			text_pushpin.SetValue(node.pushpin)
		self._edit_have_highlight = highlight_color_label
		self._edit_highlight_color = highlight_color_selector
		self._edit_opacity = opacity_slider
		self._edit_line_width = line_width_edit
		self._edit_line_color = line_color_selector
		self._edit_arrow = line_arrow_checkbox
		self._edit_background_nontrasparent = text_background_color_label
		self._edit_background_color = text_background_color_selector
		self._edit_pushpin = text_pushpin
		return extra_sizers

	def __init__(self, parent, node = None):
		wx.Dialog.__init__(self, parent, title = 'Overprinted annotation (hyperlink) properties')
		self._node = node
		sizer = wx.BoxSizer(wx.VERTICAL)
		self.Bind(wx.lib.colourselect.EVT_COLOURSELECT, self.on_select_color)
		main_properties_box_sizer = self._setup_main_properties_box()
		shape_box_sizer = self._setup_shape_box()
		border_box_sizer = self._setup_border_box()
		extra_sizers = self._setup_extra_boxes()
		for box_sizer in [main_properties_box_sizer, shape_box_sizer, border_box_sizer] + extra_sizers:
			sizer.Add(box_sizer, 0, wx.EXPAND | wx.ALL, 5)
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
		self.SetSizer(sizer)
		self.Fit()
		self._sizer = sizer
		if self._node is None:
			i, shape = 0, SHAPE_RECTANGLE
		else:
			symbol = self._node.SYMBOL
			for i, shape in enumerate(SHAPES):
				if shape.symbol == symbol:
					break
			else:
				raise TypeError
		self._edit_shape.SetSelection(i)
		self.do_select_shape(shape)
	
	def on_select_color(self, event):
		wx.CallAfter(lambda: self.radio_border_solid.SetValue(1))

__all__ = 'MapareaPropertiesDialog'

# vim:ts=4 sw=4
