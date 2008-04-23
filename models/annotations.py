#!/usr/bin/python
# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>

import djvu.const

from models import MultiPageModel
from varietes import not_overridden


class Border(object):

	def __init__(self, *args, **kwargs):
		pass # FIXME

class XorBorder(Border):
	pass

class SolidBorder(Border):
	pass

class BorderShadow(Border):
	pass

class BorderShadowIn(BorderShadow):
	pass

class BorderShadowOut(BorderShadow):
	pass

class BorderEtchedIn(BorderShadow):
	pass

class BorderEtchedOut(BorderShadow):
	pass

class Annotations(MultiPageModel):

	def get_page_model_class(self, n):
		cls = PageAnnotations
		if n == SHARED_ANNOTATIONS_PAGENO:
			return SharedAnnotations
		else:
			return PageAnnotations

class MapArea(object):

	@not_overridden
	def __init__(self, *args, **kwargs):
		pass

	@classmethod 
	def from_sexpr(cls, sexpr):
		sexpr = iter(sexpr)
		symbol = sexpr.next().value
		if symbol is not djvu.const.ANNOTATION_MAPAREA:
			raise ValueError
		href = sexpr.next().value
		try:
			symbol, href, target = href
		except (TypeError, ValueError):
			target = None
		else:
			if symbol is not djvu.const.MAPAREA_HREF:
				raise ValueError
		comment = sexpr.next().value
		shape = sexpr.next()
		shape_iter = iter(shape)
		cls = MAPAREA_SHAPE_TO_CLASS[shape_iter.next().value]
		args = [int(item) for item in shape_iter]
		kwargs = {}
		for item in sexpr:
			try:
				key, value = item
				key = key.value
				value = value.value
			except TypeError:
				key, = item
				key = key.value
				value = True
			kwargs['s_%s' % key] = value
		return cls(*args, **kwargs)

	def _parse_border_options(self, options):
		self._border = None
		try:
			del options['s_none']
		except KeyError:
			pass
		try:
			del options['s_xor']
		except KeyError:
			pass
		else:
			self._border = XorBorder()
		try:
			self._border = SolidBorder(self._parse_color(options.pop('s_border')))
		except KeyError:
			pass
		for border_style in djvu.const.MAPAREA_SHADOW_BORDERS:
			try:
				width = self._parse_width(options.pop('s_%s' % border_style))
			except KeyError:
				continue
			cls = MAPAREA_SHADOW_BORDER_TO_CLASS[border_style]
			self._border = cls(width)

	def _check_invalid_options(self, options):
		if options:
			raise ValueError('%r is invalid keyword argument for this function' % (iter(options).next(),))
	
	def _parse_color(self, color):
		# FIXME
		return color
	
	def _parse_xywh(self, x, y, w, h):
		x, y, w, h = map(int, (x, y, w, h))
		if w <= 0 or h <= 0:
			raise ValueError
		self._x, self._y, self._w, self._h = x, y, w, h
	
	def _parse_width(self, w):
		w = int(w)
		if w < 0:
			raise ValueError
		return w

class RectangleMapArea(MapArea):

	def __init__(self, x, y, w, h, **options):
		self._parse_xywh(x, y, w, h)
		self._parse_border_options(options)
		try:
			self._highlight_color = self._parse_color(options.pop('s_hilite'))
		except KeyError:
			self._highlight_color = None
		try:
			self._opacity = int(options.pop('s_opacity'))
			if not (0 <= self._opacity <= 100):
				raise ValueError
		except KeyError:
			self._opacity = 50
		self._check_invalid_options(options)

class OvalMapArea(MapArea):

	def __init__(self, x, y, w, h, **options):
		self._parse_xywh(x, y, w, h)
		self._parse_border_options(options)
		self._check_invalid_options(options)

class PolygonMapArea(MapArea):

	def __init__(self, *coords, **options):
		self._parse_border_options(options)
		self._check_invalid_options(options)

class LineMapArea(MapArea):

	def __init__(self, x1, y1, x2, y2, **options):
		try:
			del options['s_arrow']
		except KeyError:
			self._arrow = False
		else:
			self._arrow = True
		try:
			self._width = int(options.pop('s_width'))
			if self._width < 1:
				raise ValueError
		except KeyError:
			self._width = 1
		try:
			self._line_color = self._parse_color(options.pop('s_lineclr'))
		except KeyError:
			self._line_color = None
		self._check_invalid_options(options)

class TextMapArea(MapArea):

	def __init__(self, x, y, w, h, **options):
		self._parse_xywh(x, y, w, h)
		self._parse_border_options(options)
		try:
			self._background_color = self._parse_color(options.pop('s_backclr'))
		except KeyError:
			self._background_color = None
		try:
			self._text_color = self._parse_color(options.pop('s_textclr'))
		except KeyError:
			self._text_color = None
		try:
			del options['s_pushpin']
		except KeyError:
			self._push_pin = False
		else:
			self._push_pin = True
		self._check_invalid_options(options)

MAPAREA_SHADOW_BORDER_TO_CLASS = \
{
	djvu.const.MAPAREA_BORDER_SHADOW_IN:  BorderShadowIn,
	djvu.const.MAPAREA_BORDER_SHADOW_OUT: BorderShadowOut,
	djvu.const.MAPAREA_BORDER_ETCHED_IN:  BorderEtchedIn,
	djvu.const.MAPAREA_BORDER_ETCHED_OUT: BorderEtchedOut
}

MAPAREA_SHAPE_TO_CLASS = \
{
	djvu.const.MAPAREA_SHAPE_RECTANGLE : RectangleMapArea,
	djvu.const.MAPAREA_SHAPE_OVAL      : OvalMapArea,
	djvu.const.MAPAREA_SHAPE_POLYGON   : PolygonMapArea,
	djvu.const.MAPAREA_SHAPE_LINE      : LineMapArea,
	djvu.const.MAPAREA_SHAPE_TEXT      : TextMapArea,
}

ANNOTATION_TYPE_TO_CLASS = \
{
	djvu.const.ANNOTATION_MAPAREA: MapArea
}

class PageAnnotations(object):

	def __init__(self, n, original_data):
		self._old_data = original_data
		self.revert()
	
	def revert(self):
		self._data = self._classify_data(self._old_data)
		self._dirty = False
	
	def export(self, djvused):
		if not self._dirty:
			return
		self.export_select(djvused)
		djvused.set_annotations(self._data)

	def export_select(self, djvused):
		djvused.select(self._n + 1)

class SharedAnnotations(object):

	def export_select(self, djvused):
		djvused.create_shared_annotations()
			

# vim:ts=4 sw=4
