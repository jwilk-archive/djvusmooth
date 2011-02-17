# encoding=UTF-8
# Copyright © 2008, 2009, 2010 Jakub Wilk <jwilk@jwilk.net>
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
import wx.lib.colourselect

import djvu.const

import djvusmooth.models.annotations
from djvusmooth import models
from djvusmooth.varietes import idict
from djvusmooth.i18n import _

# See:
# <http://www.w3.org/TR/html4/present/frames.html#target-info>,
# <http://www.w3.org/TR/html4/types.html#type-frame-target>
# for details.

HTML_TARGETS = '_blank _self _parent _top'.split()

class Shape(idict):
    def __init__(self, **kwargs):
        kwargs.setdefault('enabled', True)
        idict.__init__(self, **kwargs)

SHAPE_TEXT = Shape(label = _('Text'), model_class = models.annotations.TextMapArea)
SHAPE_LINE = Shape(label = _('Line'), model_class = models.annotations.LineMapArea, enabled=False)
SHAPE_RECTANGLE = Shape(label = _('Rectangle'), model_class = models.annotations.RectangleMapArea)
SHAPES = (
    SHAPE_RECTANGLE,
    Shape(label = _('Oval'), model_class = models.annotations.OvalMapArea),
    Shape(label = _('Polygon'), model_class = models.annotations.PolygonMapArea, enabled=False),
    SHAPE_LINE,
    SHAPE_TEXT,
)

SHADOW_BORDERS = (
    idict(model_class = models.annotations.BorderShadowIn,  label = _('Shadow in')),
    idict(model_class = models.annotations.BorderShadowOut, label = _('Shadow out')),
    idict(model_class = models.annotations.BorderEtchedIn,  label = _('Etched in')),
    idict(model_class = models.annotations.BorderEtchedOut, label = _('Etched out'))
)

def color_as_html(color):
    return '#%02x%02x%02x' % color.Get()

class MapareaPropertiesDialog(wx.Dialog):

    DEFAULT_TEXT_WIDTH = 200
    DEFAULT_SPIN_WIDTH = 50

    def _setup_main_properties_box(self):
        node = self._node
        box = wx.StaticBox(self, label = _('Main properties'))
        box_sizer = wx.StaticBoxSizer(box)
        grid_sizer = wx.FlexGridSizer(0, 2, 5, 5)
        uri_label = wx.StaticText(self, label = 'URI: ')
        uri_edit = wx.TextCtrl(self, size = (self.DEFAULT_TEXT_WIDTH, -1))
        if node is not None:
            uri_edit.SetValue(self._node.uri)
        target_label = wx.StaticText(self, label = _('Target frame') + ': ')
        target_edit = wx.ComboBox(self,
            size = (self.DEFAULT_TEXT_WIDTH, -1),
            style = wx.CB_DROPDOWN,
            choices = HTML_TARGETS
        )
        if node is not None:
            target_edit.SetValue(self._node.target or '')
        comment_label = wx.StaticText(self, label = _('Comment') + ': ')
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
            label = _('Shape'),
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
        can_have_shadow_border = shape.model_class.can_have_shadow_border()
        for widget in self._edit_border_shadows:
            widget.Enable(can_have_shadow_border)
        self.Fit()

    def on_select_shape(self, event):
        shape = SHAPES[event.GetInt()]
        self.do_select_shape(shape)

    def enable_border_width(self, enable):
        for widget in self._edit_border_width, self._label_border_thickenss:
            widget.Enable(enable)

    def enable_solid_border(self, enable):
        self._edit_border_solid_color.Enable(enable)

    def enable_always_visible_border(self, enable):
        self._edit_border_always_visible.Enable(enable)

    def on_select_no_border(self, event):
        self.enable_always_visible_border(False)
        self.enable_border_width(False)
        self.enable_solid_border(False)

    def on_select_solid_border(self, event):
        self.enable_always_visible_border(True)
        self.enable_border_width(False)
        self.enable_solid_border(True)

    def on_select_nonshadow_border(self, event):
        self.enable_always_visible_border(True)
        self.enable_border_width(False)
        self.enable_solid_border(False)

    def on_select_shadow_border(self, event):
        self.enable_always_visible_border(True)
        self.enable_border_width(True)
        self.enable_solid_border(False)

    def _setup_border_box(self):
        node = self._node
        try:
            border = node.border
        except AttributeError:
            border = None
        box = wx.StaticBox(self, label = _('Border'))
        box_sizer = wx.StaticBoxSizer(box, orient = wx.VERTICAL)
        box_grid_sizer = wx.FlexGridSizer(0, 3, 5, 10)
        border_width_sizer = wx.BoxSizer(wx.HORIZONTAL)
        border_width_label = wx.StaticText(self, label = _('Width') + ': ')
        border_width_edit = wx.SpinCtrl(self, size = (self.DEFAULT_SPIN_WIDTH, -1))
        border_width_edit.SetRange(djvu.const.MAPAREA_SHADOW_BORDER_MIN_WIDTH, djvu.const.MAPAREA_SHADOW_BORDER_MAX_WIDTH)
        border_width_edit.SetValue(djvu.const.MAPAREA_SHADOW_BORDER_MIN_WIDTH)
        border_width_sizer.Add(border_width_label, 0, wx.ALIGN_CENTER_VERTICAL)
        border_width_sizer.Add(border_width_edit, 0, wx.ALIGN_CENTER_VERTICAL)
        radio_none = wx.RadioButton(self, label = _('None'))
        radio_xor = wx.RadioButton(self, label = _('XOR'))
        if isinstance(border, models.annotations.XorBorder):
            radio_xor.SetValue(True)
        radio_solid = wx.RadioButton(self, label = _('Solid color') + ': ')
        solid_color_selector = wx.lib.colourselect.ColourSelect(self, wx.ID_ANY)
        if isinstance(border, models.annotations.SolidBorder):
            radio_solid.SetValue(True)
            solid_color_selector.Enable(True)
            solid_color_selector.SetColour(border.color)
        else:
            solid_color_selector.Enable(False)
        solid_sizer = wx.BoxSizer(wx.HORIZONTAL)
        solid_sizer.Add(radio_solid, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT)
        solid_sizer.Add(solid_color_selector, 0, wx.ALIGN_CENTER_VERTICAL)
        for widget in radio_none, radio_xor, solid_sizer:
            box_grid_sizer.Add(widget, 0, wx.ALIGN_CENTER_VERTICAL)
        shadow_widgets = []
        have_shadow_border = False
        for i, shadow_border in enumerate(SHADOW_BORDERS):
            if i == 2:
                box_grid_sizer.Add(border_width_sizer, 0, wx.ALIGN_CENTER_VERTICAL)
            widget = wx.RadioButton(self, label = shadow_border.label)
            if isinstance(border, shadow_border.model_class):
                widget.SetValue(True)
                have_shadow_border = True
            widget.model_class = shadow_border.model_class
            box_grid_sizer.Add(widget, 0, wx.ALIGN_CENTER_VERTICAL)
            shadow_widgets += widget,
        for widget in shadow_widgets:
            self.Bind(wx.EVT_RADIOBUTTON, self.on_select_shadow_border, widget)
        self.Bind(wx.EVT_RADIOBUTTON, self.on_select_nonshadow_border, radio_xor)
        self.Bind(wx.EVT_RADIOBUTTON, self.on_select_no_border, radio_none)
        self.Bind(wx.EVT_RADIOBUTTON, self.on_select_solid_border, radio_solid)
        avis_checkbox = wx.CheckBox(self, label = _('Always visible')) # TODO: hide it for irrelevant shapes, i.e. `line` and maybe `text`
        if border is None or isinstance(border, models.annotations.NoBorder):
            avis_checkbox.Enable(False)
        elif node is not None and node.border_always_visible is True:
            avis_checkbox.SetValue(True)
        box_sizer.Add(box_grid_sizer, 0, wx.EXPAND | wx.ALL, 5)
        box_sizer.Add(avis_checkbox, 0, wx.ALL, 5)
        self._edit_border_none = radio_none
        self._edit_border_xor = radio_xor
        self._edit_border_solid = radio_solid
        self._edit_border_solid_color = solid_color_selector
        self._edit_border_shadows = shadow_widgets
        self._edit_border_always_visible = avis_checkbox
        self._edit_border_width = border_width_edit
        self._label_border_thickenss = border_width_label
        self.enable_border_width(have_shadow_border)
        if have_shadow_border:
            border_width_edit.SetValue(border.width)
        return box_sizer

    def _setup_extra_boxes(self):
        node = self._node
        extra_boxes = \
        [
            wx.StaticBox(self, label = label)
            for label in (_('Highlight color and opacity'), _('Line-specific properties'), _('Text-specific properties'))
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
        highlight_color_label = wx.CheckBox(self, label = _('Highlight color') + ': ')
        highlight_color_selector = wx.lib.colourselect.ColourSelect(self, wx.ID_ANY)
        highlight_color_selector.SetColour(wx.BLUE)
        highlight_color_selector.Enable(False)
        def on_switch_highlight_color(event):
            highlight_color_selector.Enable(event.IsChecked())
        self.Bind(wx.EVT_CHECKBOX, on_switch_highlight_color, highlight_color_label)
        opacity_label = wx.StaticText(self, label = _('Opacity') + ': ')
        opacity_slider = wx.Slider(self,
            value = djvu.const.MAPAREA_OPACITY_DEFAULT,
            size = (self.DEFAULT_TEXT_WIDTH, -1),
            style = wx.SL_HORIZONTAL | wx.SL_AUTOTICKS | wx.SL_LABELS
        )
        for widget in highlight_color_label, highlight_color_selector, opacity_label, opacity_slider:
            highlight_specific_sizer.Add(widget, 0, wx.ALIGN_CENTER_VERTICAL)
        if isinstance(node, models.annotations.RectangleMapArea):
            if node.highlight_color is None:
                highlight_color_label.SetValue(False)
                highlight_color_selector.Enable(False)
            else:
                highlight_color_label.SetValue(True)
                highlight_color_selector.Enable(True)
                highlight_color_selector.SetColour(node.highlight_color)
            opacity_slider.SetValue(node.opacity)
        line_width_label = wx.StaticText(self, label = _('Line width') + ': ')
        line_width_edit = wx.SpinCtrl(self, size = (self.DEFAULT_SPIN_WIDTH, -1))
        line_width_edit.SetRange(djvu.const.MAPAREA_LINE_MIN_WIDTH, 99)
        line_width_edit.SetValue(djvu.const.MAPAREA_LINE_MIN_WIDTH)
        line_color_label = wx.StaticText(self, label = _('Line color') + ': ')
        line_color_selector = wx.lib.colourselect.ColourSelect(self, wx.ID_ANY)
        line_arrow_checkbox = wx.CheckBox(self, label = _('Arrow'))
        dummy = (0, 0)
        for widget in line_arrow_checkbox, dummy, line_width_label, line_width_edit, line_color_label, line_color_selector:
            line_specific_sizer.Add(widget, 0, wx.ALIGN_CENTER_VERTICAL)
        if isinstance(node, models.annotations.LineMapArea):
            line_width_edit.SetValue(node.line_width)
            line_color_selector.SetColour(node.line_color)
            line_arrow_checkbox.SetValue(node.line_arrow)
        else:
            line_color_selector.SetColour(djvu.const.MAPAREA_LINE_COLOR_DEFAULT)
        text_background_color_label = wx.CheckBox(self, label = _('Background color') + ': ')
        text_background_color_selector = wx.lib.colourselect.ColourSelect(self, wx.ID_ANY)
        text_background_color_selector.SetColour(wx.WHITE)
        text_background_color_selector.Enable(False)
        def on_switch_text_background_color(event):
            text_background_color_selector.Enable(event.IsChecked())
        self.Bind(wx.EVT_CHECKBOX, on_switch_text_background_color, text_background_color_label)
        text_color_label = wx.StaticText(self, label = _('Text color') + ': ')
        text_color_selector = wx.lib.colourselect.ColourSelect(self, wx.ID_ANY)
        text_pushpin = wx.CheckBox(self, label = _('Pushpin'))
        for widget in text_background_color_label, text_background_color_selector, text_color_label, text_color_selector, text_pushpin:
            text_specific_sizer.Add(widget, 0, wx.ALIGN_CENTER_VERTICAL)
        if isinstance(node, models.annotations.TextMapArea):
            if node.background_color is not None:
                text_background_color_label.SetValue(True)
                text_background_color_selector.Enable(True)
                text_background_color_selector.SetColour(node.background_color)
            else:
                text_background_color_label.SetValue(False)
                text_background_color_selector.Enable(False)
            text_color_selector.SetColour(node.text_color)
            text_pushpin.SetValue(node.pushpin)
        else:
            text_color_selector.SetColour(djvu.const.MAPAREA_LINE_COLOR_DEFAULT)
        self._edit_have_highlight = highlight_color_label
        self._edit_highlight_color = highlight_color_selector
        self._edit_opacity = opacity_slider
        self._edit_line_width = line_width_edit
        self._edit_line_color = line_color_selector
        self._edit_arrow = line_arrow_checkbox
        self._edit_background_nontrasparent = text_background_color_label
        self._edit_background_color = text_background_color_selector
        self._edit_text_color = text_color_selector
        self._edit_pushpin = text_pushpin
        return extra_sizers

    def __init__(self, parent, node=None, origin=None):
        wx.Dialog.__init__(self, parent, title = _('Overprinted annotation (hyperlink) properties'))
        self._node = node
        if origin is None:
            self._origin = None
        else:
            self._origin = tuple(origin)
            if len(self._origin) != 2:
                raise ValueError
        sizer = wx.BoxSizer(wx.VERTICAL)
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
            for i, shape in enumerate(SHAPES):
                if isinstance(node, shape.model_class):
                    break
            else:
                raise TypeError
        self._edit_shape.SetSelection(i)
        self.do_select_shape(shape)

    def get_node(self):
        shape = SHAPES[self._edit_shape.GetSelection()]
        model_class = shape.model_class
        node = model_class.from_maparea(self._node, owner=None)
        node.uri = self._edit_uri.GetValue()
        node.target = self._edit_target.GetValue() or None
        node.comment = self._edit_comment.GetValue()
        if self._edit_border_none.GetValue():
            node.border = models.annotations.NoBorder()
        elif self._edit_border_xor.GetValue():
            node.border = models.annotations.XorBorder()
        elif self._edit_border_solid.GetValue():
            color = color_as_html(self._edit_border_solid_color.GetColour())
            node.border = models.annotations.SolidBorder(color)
        elif model_class.can_have_shadow_border():
            for widget in self._edit_border_shadows:
                if widget.GetValue():
                    node.border = widget.model_class(self._edit_border_width.GetValue())
                    break
        node.border_always_visible = (
            self._edit_border_always_visible.IsEnabled() and
            self._edit_border_always_visible.GetValue()
        )
        if isinstance(node, models.annotations.RectangleMapArea):
            if self._edit_have_highlight.GetValue():
                node.highlight_color = color_as_html(self._edit_highlight_color.GetColour())
            else:
                node.highlight_color = None
            node.opacity = self._edit_opacity.GetValue()
        elif isinstance(node, models.annotations.LineMapArea):
            node.line_width = self._edit_line_width.GetValue()
            node.line_color = color_as_html(self._edit_line_color.GetColour())
            node.line_arrow = self._edit_arrow.GetValue()
        elif isinstance(node, models.annotations.TextMapArea):
            if self._edit_background_nontrasparent.GetValue():
                node.background_color = color_as_html(self._edit_background_color.GetColour())
            else:
                node.background_color = None
            node.text_color = color_as_html(self._edit_text_color.GetColour())
            node.pushpin = self._edit_pushpin.GetValue()
        if self._origin:
            node.origin = self._origin
        return node

    node = property(get_node)

__all__ = 'MapareaPropertiesDialog'

# vim:ts=4 sw=4 et
