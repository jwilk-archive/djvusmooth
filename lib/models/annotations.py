# encoding=UTF-8
# Copyright © 2008, 2009, 2010 Jakub Wilk <jwilk@jwilk.net>
#
# This package is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 dated June, 1991.
#
# This package is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

'''
Models for annotations.

See Lizardtech DjVu Reference (DjVu 3):
- 3.3.1 Annotations.
- 8.3.4 Annotation chunk.
'''

import weakref
import itertools

import djvu.const
import djvu.sexpr
import djvu.decode

from djvusmooth.models import MultiPageModel, SHARED_ANNOTATIONS_PAGENO
from djvusmooth.varietes import not_overridden, is_html_color

class AnnotationSyntaxError(ValueError):
    pass

class MapAreaSyntaxError(AnnotationSyntaxError):
    pass

def parse_color(color, allow_none=False):
    if allow_none and color is None:
        return
    color = str(color).upper()
    if not is_html_color(color):
        raise ValueError('%r is not a valid color' % (color,))
    return color

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

    @not_overridden
    def notify_node_add(self, node):
        pass

    @not_overridden
    def notify_node_delete(self, node):
        pass

    @not_overridden
    def notify_node_replace(self, node, other_node):
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
        self._color = parse_color(color)

    @property
    def color(self):
        return self._color

    def _get_sexpr(self):
        return djvu.sexpr.Expression((djvu.const.MAPAREA_BORDER_SOLID_COLOR, djvu.sexpr.Symbol(self._color)))

class BorderShadow(Border):

    def __init__(self, width):
        width = int(width)
        if not djvu.const.MAPAREA_SHADOW_BORDER_MIN_WIDTH <= width <= djvu.const.MAPAREA_SHADOW_BORDER_MAX_WIDTH:
            raise ValueError
        self._width = width

    @property
    def width(self):
        return self._width

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
        if n == SHARED_ANNOTATIONS_PAGENO:
            return SharedAnnotations
        else:
            return PageAnnotations

class Annotation(object):

    @classmethod
    def from_sexpr(cls, sexpr, owner):
        raise NotImplementedError

    @not_overridden
    def _get_sexpr(self):
        raise NotImplementedError

    @apply
    def sexpr():
        def get(self):
            return self._get_sexpr()
        return property(get)

class OtherAnnotation(Annotation):

    def __init__(self, sexpr, owner=None):
        self._sexpr = sexpr

    @classmethod
    def from_sexpr(cls, sexpr, owner):
        return cls(sexpr, owner)

    def _get_sexpr(self):
        return self._sexpr

class MapArea(Annotation):

    DEFAULT_ARGUMENTS = NotImplemented

    @classmethod
    def can_have_shadow_border(cls):
        return False

    def replace(self, other):
        if not isinstance(other, MapArea):
            raise TypeError
        if self._owner is None:
            return
        self._owner.replace_maparea(self, other)
        other._owner = self._owner

    def delete(self):
        former_owner = self._owner
        if former_owner is None:
            return
        self._owner.remove_maparea(self)
        self._owner = None

    def insert(self, owner):
        owner.add_maparea(self)
        self._owner = owner

    @classmethod
    def from_maparea(cls, maparea, owner):
        if maparea is None:
            uri = comment = ''
            target = None
        else:
            uri = maparea.uri
            target = maparea.target
            comment = maparea.comment
        self = cls(
            *cls.DEFAULT_ARGUMENTS,
            **dict(
                uri = uri,
                target = target,
                comment = comment,
                owner = owner
            )
        )
        if maparea is None:
            self._border = NoBorder()
        else:
            self._border = maparea.border
        if isinstance(self._border, BorderShadow) and not cls.can_have_shadow_border():
            self._border = NoBorder()
        self._border_always_visible = maparea is not None and maparea.border_always_visible is True
        return self

    @classmethod
    def from_sexpr(cls, sexpr, owner):
        sexpr = iter(sexpr)
        try:
            symbol = sexpr.next().value
            if symbol is not djvu.const.ANNOTATION_MAPAREA:
                raise MapAreaSyntaxError
            uri = sexpr.next().value
            if isinstance(uri, tuple):
                symbol, uri, target = uri
                if symbol is not djvu.const.MAPAREA_URI:
                    raise MapAreaSyntaxError
                target = target.decode('UTF-8', 'replace')
            else:
                target = None
            uri = uri.decode('UTF-8')
            comment = sexpr.next().value.decode('UTF-8', 'replace')
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
        except (StopIteration, TypeError), ex:
            raise MapAreaSyntaxError(ex)
        return cls(*args, **kwargs)

    @not_overridden
    def _get_sexpr_area(self):
        raise NotImplementedError

    @not_overridden
    def _get_sexpr_extra(self):
        return ()

    def _get_sexpr_border(self):
        if self._border is None:
            return
        return self._border.sexpr

    def _get_sexpr(self):
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
            self._border = SolidBorder(parse_color(options.pop('s_%s' % djvu.const.MAPAREA_BORDER_SOLID_COLOR)))
        except KeyError:
            pass
        except (TypeError, ValueError), ex:
            raise MapAreaSyntaxError(ex)

    def _parse_shadow_border_options(self, options):
        for border_style in djvu.const.MAPAREA_SHADOW_BORDERS:
            try:
                width = self._parse_width(options.pop('s_%s' % border_style))
            except KeyError:
                continue
            except (TypeError, ValueError), ex:
                raise MapAreaSyntaxError(ex)
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
        for option in options:
            if option.startswith('s_'):
                raise MapAreaSyntaxError('%r is invalid option for %r annotations' % (option[2:], self.SYMBOL))
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

    @not_overridden
    def _set_rect(self, rect):
        raise NotImplementedError

    @not_overridden
    def _get_rect(self):
        raise NotImplementedError

    def _get_orign(self):
        return self._get_rect()[:2]

    def _set_origin(self, (x1, y1)):
        x0, y0, w, h = self._get_rect()
        self._set_rect((x1, y1, w, h))

    @apply
    def origin():
        def get(self):
            return self._get_origin()
        def set(self, rect):
            self._set_origin(rect)
            self._notify_change()
        return property(get, set)

    @apply
    def rect():
        def get(self):
            return self._get_rect()
        def set(self, rect):
            self._set_rect(rect)
            self._notify_change()
        return property(get, set)

    @apply
    def border_always_visible():
        def get(self):
            return self._border_always_visible
        def set(self, value):
            self._border_always_visible = value
            self._notify_change()
        return property(get, set)

    @apply
    def border():
        def get(self):
            return self._border
        def set(self, border):
            if not isinstance(border, Border):
                raise TypeError
            if not self.can_have_shadow_border() and isinstance(border, BorderShadow):
                raise TypeError
            self._border = border
            self._notify_change()
        return property(get, set)

    def _parse_width(self, w):
        w = int(w)
        if w < 0:
            raise ValueError
        return w

    def _notify_change(self):
        if self._owner is None:
            return
        return self._owner.notify_node_change(self)

    def notify_select(self):
        if self._owner is None:
            return
        self._owner.notify_node_select(self)

    def notify_deselect(self):
        if self._owner is None:
            return
        self._owner.notify_node_deselect(self)

class XywhMapArea(MapArea):

    DEFAULT_ARGUMENTS = (0, 0, 32, 32)

    @classmethod
    def from_maparea(cls, maparea, owner):
        self = super(XywhMapArea, cls).from_maparea(maparea, owner)
        if maparea is not None:
            self._set_rect(maparea.rect)
        return self

    def _parse_xywh(self, x, y, w, h):
        x, y, w, h = map(int, (x, y, w, h))
        if w <= 0 or h <= 0:
            raise ValueError
        self._x, self._y, self._w, self._h = x, y, w, h

    def _set_rect(self, (x, y, w, h)):
        self._parse_xywh(x, y, w, h)

    def _get_rect(self):
        return self._x, self._y, self._w, self._h

    def _get_sexpr_area(self):
        return (self.SYMBOL, self._x, self._y, self._w, self._h)

class RectangleMapArea(XywhMapArea):

    SYMBOL = djvu.const.MAPAREA_SHAPE_RECTANGLE

    @classmethod
    def can_have_shadow_border(cls):
        return True

    @classmethod
    def from_maparea(cls, maparea, owner):
        self = super(RectangleMapArea, cls).from_maparea(maparea, owner)
        if isinstance(maparea, RectangleMapArea):
            self._opacity = maparea.opacity
            self._highlight_color = maparea.highlight_color
        return self

    def __init__(self, x, y, w, h, **options):
        self._parse_xywh(x, y, w, h)
        self._parse_border_options(options)
        self._parse_shadow_border_options(options)
        self._parse_border_always_visible(options)
        try:
            self._highlight_color = parse_color(options.pop('s_%s' % djvu.const.MAPAREA_HIGHLIGHT_COLOR))
        except KeyError:
            self._highlight_color = None
        except (TypeError, ValueError), ex:
            raise MapAreaSyntaxError(ex)
        try:
            self._opacity = int(options.pop('s_%s' % djvu.const.MAPAREA_OPACITY))
            if not (djvu.const.MAPAREA_OPACITY_MIN <= self._opacity <= djvu.const.MAPAREA_OPACITY_MAX):
                raise MapAreaSyntaxError
        except KeyError:
            self._opacity = djvu.const.MAPAREA_OPACITY_DEFAULT
        except (TypeError, ValueError), ex:
            raise MapAreaSyntaxError(ex)
        self._parse_common_options(options)
        self._check_invalid_options(options)

    def _get_sexpr_extra(self):
        result = []
        if self._opacity != djvu.const.MAPAREA_OPACITY_DEFAULT:
            result += (djvu.const.MAPAREA_OPACITY, self._opacity),
        if self._highlight_color is not None:
            result += (djvu.const.MAPAREA_HIGHLIGHT_COLOR, djvu.sexpr.Symbol(self._highlight_color)),
        return tuple(result)

    @apply
    def opacity():
        def get(self):
            return self._opacity
        def set(self, value):
            value = int(value)
            if not (djvu.const.MAPAREA_OPACITY_MIN <= self._opacity <= djvu.const.MAPAREA_OPACITY_MAX):
                raise ValueError
            self._opacity = value
            self._notify_change()
        return property(get, set)

    @apply
    def highlight_color():
        def get(self):
            return self._highlight_color
        def set(self, value):
            self._highlight_color = parse_color(value, allow_none=True)
            self._notify_change()
        return property(get, set)

class OvalMapArea(XywhMapArea):

    SYMBOL = djvu.const.MAPAREA_SHAPE_OVAL

    def __init__(self, x, y, w, h, **options):
        self._parse_xywh(x, y, w, h)
        self._parse_border_options(options)
        self._parse_border_always_visible(options)
        self._parse_common_options(options)
        self._check_invalid_options(options)

    def _get_sexpr_extra(self):
        return ()

class PolygonMapArea(MapArea):

    SYMBOL = djvu.const.MAPAREA_SHAPE_POLYGON
    DEFAULT_ARGUMENTS = (0, 0, 32, 0, 32, 32, 0, 32, 32, 32)

    def _get_sexpr_area(self):
        return djvu.sexpr.Expression(itertools.chain(
            (self.SYMBOL,),
            itertools.chain(*self._coords)
        ))

    def _get_sexpr_extra(self):
        return ()

    def _get_rect(self):
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

    def _set_rect(self, rect):
        xform = djvu.decode.AffineTransform(self.rect, rect)
        self._coords = map(xform, self._coords)
        self._notify_change()

    @classmethod
    def from_maparea(cls, maparea, owner):
        self = super(PolygonMapArea, cls).from_maparea(maparea, owner)
        if isinstance(maparea, PolygonMapArea):
            self._coords = maparea.coordinates
        elif maparea is not None:
            self._set_rect(maparea.rect)
        return self

    @apply
    def coordinates():
        def get(self):
            return self._coords
        return property(get)

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
    DEFAULT_ARGUMENTS = (0, 0, 32, 32)

    def _get_sexpr_area(self):
        return djvu.sexpr.Expression((self.SYMBOL, self._x0, self._y0, self._x1, self._y1))

    def _get_sexpr_extra(self):
        result = []
        if self._line_arrow:
            result += (djvu.const.MAPAREA_ARROW,),
        if self._line_width != djvu.const.MAPAREA_LINE_MIN_WIDTH:
            result += (djvu.const.MAPAREA_LINE_WIDTH, self._line_width),
        if self._line_color != djvu.const.MAPAREA_LINE_COLOR_DEFAULT:
            result += (djvu.const.MAPAREA_LINE_COLOR, self._line_color),
        return tuple(result)

    def _get_rect(self):
        x0, y0, x1, y1 = self._x0, self._y0, self._x1, self._y1
        return (min(x0, x1), min(y0, y1), abs(x0 - x1), abs(y0 - y1))

    def _set_rect(self, rect):
        xform = djvu.decode.AffineTransform(self.rect, rect)
        self._x0, self._y0 = xform((self._x0, self._y0))
        self._x1, self._y1 = xform((self._x1, self._y1))

    @apply
    def point_from():
        def get(self):
            return self._x0, self._y0
        return property(get)

    @apply
    def point_to():
        def get(self):
            return self._x1, self._y1
        return property(get)

    @classmethod
    def from_maparea(cls, maparea, owner):
        self = super(LineMapArea, cls).from_maparea(maparea, owner)
        if isinstance(maparea, LineMapArea):
            (self._x0, self._y0), (self._x1, self._y1) = maparea.point_from, maparea.point_to
            self._line_arrow = maparea.line_arrow
            self._line_width = maparea.line_width
            self._line_color = maparea.line_color
        elif maparea is not None:
            self._set_rect(maparea.rect)
        return self

    def __init__(self, x1, y1, x2, y2, **options):
        self._x0, self._y0, self._x1, self._y1 = itertools.imap(int, (x1, y1, x2, y2))
        try:
            del options['s_%s' % djvu.const.MAPAREA_ARROW]
        except KeyError:
            self._line_arrow = False
        else:
            self._line_arrow = True
        try:
            self._line_width = int(options.pop('s_%s' % djvu.const.MAPAREA_LINE_WIDTH))
            if self._line_width < djvu.const.MAPAREA_LINE_MIN_WIDTH:
                raise ValueError
        except KeyError:
            self._line_width = djvu.const.MAPAREA_LINE_MIN_WIDTH
        except (TypeError, ValueError), ex:
            raise MapAreaSyntaxError(ex)
        try:
            self._line_color = parse_color(options.pop('s_%s' % djvu.const.MAPAREA_LINE_COLOR))
        except KeyError:
            self._line_color = djvu.const.MAPAREA_LINE_COLOR_DEFAULT
        except (TypeError, ValueError), ex:
            raise MapAreaSyntaxError(ex)
        self._parse_border_options(options)
        self._parse_common_options(options)
        self._check_invalid_options(options)

    @apply
    def line_width():
        def get(self):
            return self._line_width
        def set(self, value):
            self._line_width = value
            self._notify_change()
        return property(get, set)

    @apply
    def line_color():
        def get(self):
            return self._line_color
        def set(self, value):
            self._line_color = parse_color(value)
            self._notify_change()
        return property(get, set)

    @apply
    def line_arrow():
        def get(self):
            return self._line_arrow
        def set(self, value):
            self._line_arrow = value
            self._notify_change()
        return property(get, set)

    @apply
    def border_always_visible():
        def get(self):
            return NotImplemented
        def set(self, value):
            pass # FIXME?
        return property(get, set)

class TextMapArea(XywhMapArea):

    SYMBOL = djvu.const.MAPAREA_SHAPE_TEXT

    @classmethod
    def from_maparea(cls, maparea, owner):
        self = super(TextMapArea, cls).from_maparea(maparea, owner)
        if isinstance(maparea, TextMapArea):
            self._background_color = maparea.background_color
            self._text_color = maparea.text_color
            self._pushpin = maparea.pushpin
        return self

    def __init__(self, x, y, w, h, **options):
        self._parse_xywh(x, y, w, h)
        self._parse_border_options(options)
        self._parse_border_always_visible(options)
            # XXX Reference (8.3.4.2.3.1 Miscellaneous parameters) states that ``(border_avis)``
            # is not relevant for text annotations. Nevertheless that option can be found
            # in the wild, e.g. in the ``lizard2005-antz.djvu`` file.
        try:
            self._background_color = parse_color(options.pop('s_%s' % djvu.const.MAPAREA_BACKGROUND_COLOR))
        except KeyError:
            self._background_color = None
        except (TypeError, ValueError), ex:
            raise MapAreaSyntaxError(ex)
        try:
            self._text_color = parse_color(options.pop('s_%s' % djvu.const.MAPAREA_TEXT_COLOR))
        except KeyError:
            self._text_color = djvu.const.MAPAREA_TEXT_COLOR_DEFAULT
        except (TypeError, ValueError), ex:
            raise MapAreaSyntaxError(ex)
        try:
            del options['s_%s' % djvu.const.MAPAREA_PUSHPIN]
        except KeyError:
            self._pushpin = False
        else:
            self._pushpin = True
        self._parse_common_options(options)
        self._check_invalid_options(options)

    def _get_sexpr_extra(self):
        result = []
        if self._background_color is not None:
            result += (djvu.const.MAPAREA_BACKGROUND_COLOR, djvu.sexpr.Symbol(self._background_color)),
        if self._text_color != djvu.const.MAPAREA_TEXT_COLOR_DEFAULT:
            result += (djvu.const.MAPAREA_TEXT_COLOR, djvu.sexpr.Symbol(self._text_color)),
        if self._pushpin:
            result += (djvu.const.MAPAREA_PUSHPIN,),
        return tuple(result)

    @apply
    def background_color():
        def get(self):
            return self._background_color
        def set(self, color):
            self._background_color = parse_color(color, allow_none=True)
            self._notify_change()
        return property(get, set)

    @apply
    def text_color():
        def get(self):
            return self._text_color
        def set(self, color):
            self._text_color = parse_color(color)
            self._notify_change()
        return property(get, set)

    @apply
    def pushpin():
        def get(self):
            return self._pushpin
        def set(self, value):
            self._pushpin = value
            self._notify_change()
        return property(get, set)

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
        result = dict((key, []) for key in ANNOTATION_TYPE_TO_CLASS.itervalues())
        result[None] = []
        for item in items:
            cls = ANNOTATION_TYPE_TO_CLASS.get(item[0].value)
            if cls is not None:
                item = cls.from_sexpr(item, self)
            else:
                item = OtherAnnotation(item)
            result[cls].append(item)
        return result

    def add_maparea(self, node):
        self._data[MapArea] += node,
        self.notify_node_add(node)

    def remove_maparea(self, node):
        try:
            self._data[MapArea].remove(node)
        except ValueError:
            return
        self.notify_node_delete(node)

    def replace_maparea(self, node, other_node):
        mapareas = self._data[MapArea]
        try:
            i = mapareas.index(node)
        except ValueError:
            return
        mapareas[i] = other_node
        self.notify_node_replace(node, other_node)

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

    def notify_node_add(self, node):
        self._dirty = True
        for callback in self._callbacks:
            callback.notify_node_add(node)

    def notify_node_change(self, node):
        self._dirty = True
        for callback in self._callbacks:
            callback.notify_node_change(node)

    def notify_node_replace(self, node, other_node):
        self._dirty = True
        for callback in self._callbacks:
            callback.notify_node_replace(node, other_node)

    def notify_node_delete(self, node):
        self._dirty = True
        for callback in self._callbacks:
            callback.notify_node_delete(node)

    def notify_node_select(self, node):
        for callback in self._callbacks: callback.notify_node_select(node)

    def notify_node_deselect(self, node):
        for callback in self._callbacks: callback.notify_node_deselect(node)

class SharedAnnotations(object):

    def export_select(self, djvused):
        djvused.create_shared_annotations()

# vim:ts=4 sw=4 et
