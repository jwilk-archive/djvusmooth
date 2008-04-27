#!/usr/bin/python
# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>

'''
Models for annotations.

See Lizardtech DjVu Reference (DjVu 3):
- 3.3.1 Annotations.
- 8.3.4 Annotation chunk.
'''

import weakref
import itertools

import djvu.const

from models import MultiPageModel, SHARED_ANNOTATIONS_PAGENO
from varietes import not_overridden

class PageAnnotationsCallback(object):

	@not_overridden
	def notify_node_change(self, node):
		pass

	@not_overridden
	def notify_node_select(self, node):
		pass

	@not_overridden
	def notify_node_deselect(self, node):
		pass

class Border(object):

	@not_overridden
	def __init__(self, *args, **kwargs):
		raise NotImplementedError
	
	@not_overridden
	def _get_sexpr(self):
		raise NotImplementedError

	@apply
	def sexpr():
		def get(self):
			return self._get_sexpr()
		return property(get)

class NoBorder(Border):

	def __init__(self):
		pass

	def _get_sexpr(self):
		return djvu.sexpr.Expression((djvu.const.MAPAREA_BORDER_NONE,))

class XorBorder(Border):

	def __init__(self):
		pass

	def _get_sexpr(self):
		return djvu.sexpr.Expression((djvu.const.MAPAREA_BORDER_XOR,))

class SolidBorder(Border):

	def __init__(self, color):
		self._color = color
	
	def _get_sexpr(self):
		return djvu.sexpr.Expression((djvu.const.MAPAREA_BORDER_SOLID_COLOR, self._color))

class BorderShadow(Border):

	def __init__(self, width):
		self._width = width

	def _get_sexpr(self):
		return djvu.sexpr.Expression((self.SYMBOL, self._width))

class BorderShadowIn(BorderShadow):
	SYMBOL = djvu.const.MAPAREA_BORDER_SHADOW_IN

class BorderShadowOut(BorderShadow):
	SYMBOL = djvu.const.MAPAREA_BORDER_SHADOW_OUT

class BorderEtchedIn(BorderShadow):
	SYMBOL = djvu.const.MAPAREA_BORDER_ETCHED_IN

class BorderEtchedOut(BorderShadow):
	SYMBOL = djvu.const.MAPAREA_BORDER_ETCHED_OUT

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
	def from_sexpr(cls, sexpr, owner):
		sexpr = iter(sexpr)
		symbol = sexpr.next().value
		if symbol is not djvu.const.ANNOTATION_MAPAREA:
			raise ValueError
		uri = sexpr.next().value
		try:
			symbol, uri, target = uri
		except (TypeError, ValueError):
			target = None
		else:
			if symbol is not djvu.const.MAPAREA_URI:
				raise ValueError
		comment = sexpr.next().value
		shape = sexpr.next()
		shape_iter = iter(shape)
		cls = MAPAREA_SHAPE_TO_CLASS[shape_iter.next().value]
		args = [int(item) for item in shape_iter]
		kwargs = dict(uri = uri, target = target, comment = comment, owner = owner)
		for item in sexpr:
			try:
				key, value = item
				key = key.value
				value = value.value
			except ValueError:
				key, = item
				key = key.value
				value = True
			kwargs['s_%s' % key] = value
		return cls(*args, **kwargs)

	@not_overridden
	def _get_sexpr_area(self):
		raise NotImplementedError
	
	def _get_sexpr_area_xywh(self):
		return (self.SYMBOL, self._x, self._y, self._w, self._h)

	@not_overridden
	def _get_sexpr_extra(self):
		return ()
	
	def _get_sexpr_border(self):
		if self._border is None:
			return
		return self._border.sexpr

	@apply
	def sexpr():
		def get(self):
			if self._target is None:
				uri_part = self._uri
			else:
				uri_part = (djvu.const.MAPAREA_URI, self._uri, self._target)
			border_part = self._get_sexpr_border()
			if border_part is None:
				border_part = ()
			else:
				border_part = (border_part,)
			if self.border_always_visible is True:
				border_part += (djvu.const.MAPAREA_BORDER_ALWAYS_VISIBLE,),
			return djvu.sexpr.Expression(
				(
					djvu.const.ANNOTATION_MAPAREA,
					uri_part,
					self._comment,
					self._get_sexpr_area(),
				) +
				border_part +
				self._get_sexpr_extra()
			)
		return property(get)
	
	def _parse_border_options(self, options):
		self._border = None
		try:
			del options['s_%s' % djvu.const.MAPAREA_BORDER_NONE]
		except KeyError:
			pass
		else:
			self._border = NoBorder()
		try:
			del options['s_%s' % djvu.const.MAPAREA_BORDER_XOR]
		except KeyError:
			pass
		else:
			self._border = XorBorder()
		try:
			self._border = SolidBorder(self._parse_color(options.pop('s_%s' % djvu.const.MAPAREA_BORDER_SOLID_COLOR)))
		except KeyError:
			pass
	
	def _parse_shadow_border_options(self, options):
		for border_style in djvu.const.MAPAREA_SHADOW_BORDERS:
			try:
				width = self._parse_width(options.pop('s_%s' % border_style))
			except KeyError:
				continue
			cls = MAPAREA_SHADOW_BORDER_TO_CLASS[border_style]
			self._border = cls(width)
	
	def _parse_border_always_visible(self, options):
		try:
			del options['s_%s' % djvu.const.MAPAREA_BORDER_ALWAYS_VISIBLE]
		except KeyError:
			self._border_always_visible = False
		else:
			self._border_always_visible = True

	def _check_invalid_options(self, options):
		if options:
			raise ValueError('%r is invalid keyword argument for this function' % (iter(options).next(),))
	
	def _parse_common_options(self, options):
		self._uri = options.pop('uri')
		self._target = options.pop('target')
		self._comment = options.pop('comment')
		self._owner = options.pop('owner')
	
	@apply
	def uri():
		def get(self):
			return self._uri
		def set(self, value):
			self._uri = value
			self._notify_change()
		return property(get, set)
	
	@apply
	def target():
		def get(self):
			return self._target
		def set(self, value):
			self._target = value
			self._notify_change()
		return property(get, set)

	@apply
	def comment():
		def get(self):
			return self._comment
		def set(self, value):
			self._comment = value
			self._notify_change()
		return property(get, set)

	@apply
	def rect():
		def not_implemented(self):
			raise NotImplementedError
		return property(not_implemented, not_implemented)
	
	@property
	def border_always_visible(self):
		return self._border_always_visible

	def _parse_color(self, color):
		# FIXME
		return color
	
	def _parse_xywh(self, x, y, w, h):
		x, y, w, h = map(int, (x, y, w, h))
		if w <= 0 or h <= 0:
			raise ValueError
		self._x, self._y, self._w, self._h = x, y, w, h
	
	@apply
	def _rect_xywh():
		def get(self):
			return self._x, self._y, self._w, self._h
		def set(self, (x, y, w, h)):
			self._parse_xywh(x, y, w, h)
			self._notify_change()
		return property(get, set)
	
	def _parse_width(self, w):
		w = int(w)
		if w < 0:
			raise ValueError
		return w

	def _notify_change(self):
		return self._owner.notify_node_change(self)

	def notify_select(self):
		self._owner.notify_node_select(self)

	def notify_deselect(self):
		self._owner.notify_node_deselect(self)

class RectangleMapArea(MapArea):

	SYMBOL = djvu.const.MAPAREA_SHAPE_RECTANGLE

	def __init__(self, x, y, w, h, **options):
		self._parse_xywh(x, y, w, h)
		self._parse_border_options(options)
		self._parse_shadow_border_options(options)
		self._parse_border_always_visible(options)
		try:
			self._highlight_color = self._parse_color(options.pop('s_%s' % djvu.const.MAPAREA_HIGHLIGHT_COLOR))
		except KeyError:
			self._highlight_color = None
		try:
			self._opacity = int(options.pop('s_%s' % djvu.const.MAPAREA_OPACITY))
			if not (0 <= self._opacity <= 100):
				raise ValueError
		except KeyError:
			self._opacity = 50
		self._parse_common_options(options)
		self._check_invalid_options(options)

	def _get_sexpr_extra(self):
		result = []
		if self._opacity is not None:
			result += (djvu.const.MAPAREA_OPACITY, self._opacity),
		if self._highlight_color is not None:
			result += (djvu.const.MAPAREA_HIGHLIGHT_COLOR, self._highlight_color),
		return tuple(result)
	
	rect = MapArea._rect_xywh
	_get_sexpr_area = MapArea._get_sexpr_area_xywh

class OvalMapArea(MapArea):

	SYMBOL = djvu.const.MAPAREA_SHAPE_OVAL

	def __init__(self, x, y, w, h, **options):
		self._parse_xywh(x, y, w, h)
		self._parse_border_options(options)
		self._parse_border_always_visible(options)
		self._parse_common_options(options)
		self._check_invalid_options(options)

	rect = MapArea._rect_xywh
	_get_sexpr_area = MapArea._get_sexpr_area_xywh

	def _get_sexpr_extra(self):
		return ()

class PolygonMapArea(MapArea):

	SYMBOL = djvu.const.MAPAREA_SHAPE_POLYGON

	def _get_sexpr_area(self):
		return djvu.sexpr.Expression(itertools.chain(
			(self.SYMBOL,),
			itertools.chain(*self._coords)
		))
	
	def _get_sexpr_extra(self):
		return ()
	
	@apply
	def rect():
		def get(self):
			x0 = y0 = 1e999
			x1 = y1 = -1e999
			for (x, y) in self._coords:
				if x < x0: x0 = x
				if y < y0: y0 = y
				if x > x1: x1 = x
				if y > y1: y1 = y
			w = x1 - x0
			h = y1 - y0
			if w <= 0: w = 1
			if h <= 0: h = 1
			return (x0, y0, w, h)
		def set(self, value):
			raise NotImplementedError
		return property(get, set)

	def __init__(self, *coords, **options):
		n_coords = len(coords)
		if n_coords & 1:
			raise ValueError('polygon with %2.f vertices' % (n_coords / 2.0))
		if n_coords < 6:
			raise ValueError('polygon with %d vertices' % (n_coords // 2))
		coords = (int(x) for x in coords)
		self._coords = zip(coords, coords)
		self._parse_border_options(options)
		self._parse_border_always_visible(options)
		self._parse_common_options(options)
		self._check_invalid_options(options)

class LineMapArea(MapArea):

	SYMBOL = djvu.const.MAPAREA_SHAPE_LINE

	def _get_sexpr_area(self):
		return djvu.sexpr.Expression((self.SYMBOL, self._x0, self._y0, self._x1, self._y1))
	
	def _get_sexpr_extra(self):
		result = []
		if self._arrow:
			result += (djvu.const.MAPAREA_ARROW,),
		if self._width != 1:
			result += (djvu.const.MAPAREA_LINE_WIDTH, self._width),
		if self._line_color is not None:
			result += (djvu.const.MAPAREA_LINE_COLOR, self._line_color),
		return tuple(result)

	@apply
	def rect():
		def get(self):
			x0, y0, x1, y1 = self._x0, self._y0, self._x1, self._y1
			return (min(x0, x1), min(y0, y1), abs(x0 - x1), abs(y0 - y1))
		def set(self, value):
			raise NotImplementedError
		return property(get, set)

	def __init__(self, x1, y1, x2, y2, **options):
		self._x0, self._y0, self._x1, self._y1 = itertools.imap(int, (x1, y1, x2, y2))
		try:
			del options['s_%s' % djvu.const.MAPAREA_ARROW]
		except KeyError:
			self._arrow = False
		else:
			self._arrow = True
		try:
			self._width = int(options.pop('s_%s' % djvu.const.MAPAREA_LINE_WIDTH))
			if self._width < 1:
				raise ValueError
		except KeyError:
			self._width = 1
		try:
			self._line_color = self._parse_color(options.pop('s_%s' % djvu.const.MAPAREA_LINE_COLOR))
		except KeyError:
			self._line_color = None
		self._parse_border_options(options)
		self._parse_common_options(options)
		self._check_invalid_options(options)
	
	@property
	def border_always_visible(self):
		return NotImplemented

class TextMapArea(MapArea):

	SYMBOL = djvu.const.MAPAREA_SHAPE_TEXT

	def __init__(self, x, y, w, h, **options):
		self._parse_xywh(x, y, w, h)
		self._parse_border_options(options)
		self._parse_border_always_visible(options)
			# XXX Reference (8.3.4.2.3.1 Miscellaneous parameters) states that ``(border_avis)``
			# is not relevant for text mapareas. Nethertheless that option can be found
			# in the wild, e.g. in the ``lizard2005-antz.djvu`` file.
		try:
			self._background_color = self._parse_color(options.pop('s_%s' % djvu.const.MAPAREA_BACKGROUND_COLOR))
		except KeyError:
			self._background_color = None
		try:
			self._text_color = self._parse_color(options.pop('s_%s' % djvu.const.MAPAREA_TEXT_COLOR))
		except KeyError:
			self._text_color = None
		try:
			del options['s_%s' % djvu.const.MAPAREA_PUSHPIN]
		except KeyError:
			self._push_pin = False
		else:
			self._push_pin = True
		self._parse_common_options(options)
		self._check_invalid_options(options)

	@property
	def border_always_visible(self):
		return NotImplemented
	# XXX Reference (8.3.4.2.3.1 Miscellaneous parameters) states that ``(border_avis)``
	# is not relevant for text mapareas. Nethertheless that option can be found
	# in the wild, e.g. in the ``lizard2005-antz.djvu`` file. So…
	del border_always_visible

	rect = MapArea._rect_xywh
	_get_sexpr_area = MapArea._get_sexpr_area_xywh

	def _get_sexpr_extra(self):
		result = []
		if self._background_color is not None:
			result += (djvu.const.MAPAREA_BACKGROUND_COLOR, self._background_color),
		if self._text_color is not None:
			result += (djvu.const.MAPAREA_TEXT_COLOR, self._text_color),
		if self._push_pin:
			result += (djvu.const.MAPAREA_PUSHPIN,),
		return tuple(result)

MAPAREA_SHADOW_BORDER_TO_CLASS = dict(
	(cls.SYMBOL, cls)
	for cls in (BorderShadowIn, BorderShadowOut, BorderEtchedIn, BorderEtchedOut)
)

MAPAREA_SHAPE_TO_CLASS = dict(
	(cls.SYMBOL, cls)
	for cls in (RectangleMapArea, OvalMapArea, PolygonMapArea, LineMapArea, TextMapArea)
)

ANNOTATION_TYPE_TO_CLASS = \
{
	djvu.const.ANNOTATION_MAPAREA: MapArea
}

class PageAnnotations(object):

	def __init__(self, n, original_data):
		self._old_data = original_data
		self._callbacks = weakref.WeakKeyDictionary()
		self.revert()
		self._n = n
	
	def register_callback(self, callback):
		if not isinstance(callback, PageAnnotationsCallback):
			raise TypeError
		self._callbacks[callback] = 1

	def _classify_data(self, items):
		result = {}
		for item in items:
			cls = ANNOTATION_TYPE_TO_CLASS.get(item[0].value)
			if cls is not None:
				item = cls.from_sexpr(item, self)
			if cls not in result:
				result[cls] = []
			result[cls].append(item)
		return result
	
	@property
	def mapareas(self):
		return self._data.get(MapArea, ())
	
	def revert(self):
		self._data = self._classify_data(self._old_data)
		self._dirty = False
	
	def export(self, djvused):
		if not self._dirty:
			return
		self.export_select(djvused)
		djvused.set_annotations(node.sexpr for nodes in self._data.itervalues() for node in nodes)

	def export_select(self, djvused):
		djvused.select(self._n + 1)

	def notify_node_change(self, node):
		self._dirty = True
		for callback in self._callbacks:
			callback.notify_node_change(node)

	def notify_node_select(self, node):
		for callback in self._callbacks: callback.notify_node_select(node)

	def notify_node_deselect(self, node):
		for callback in self._callbacks: callback.notify_node_deselect(node)

class SharedAnnotations(object):

	def export_select(self, djvused):
		djvused.create_shared_annotations()

# vim:ts=4 sw=4
