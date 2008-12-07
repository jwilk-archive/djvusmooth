# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>

import wx
import wx.lib.ogl

from math import floor

from djvu import decode, sexpr
import djvu.const

import gui.maparea_menu

import models.text
import models.annotations

from varietes import not_overridden

PIXEL_FORMAT = decode.PixelFormatRgb()
PIXEL_FORMAT.rows_top_to_bottom = 1
PIXEL_FORMAT.y_top_to_bottom = 1

RENDER_NONRASTER_TEXT = 0
RENDER_NONRASTER_MAPAREA = 1
RENDER_NONRASTER_VALUES = (RENDER_NONRASTER_TEXT, RENDER_NONRASTER_MAPAREA, None)

class Zoom(object):

    @not_overridden
    def rezoom_on_resize(self):
        raise NotImplementedError

    @not_overridden
    def get_page_screen_size(self, page_job, viewport_size):
        raise NotImplementedError

    def _get_percent(self):
        raise ValueError
    
    @apply
    def percent():
        def get(self):
            return self._get_percent()
        return property(get)

class PercentZoom(Zoom):

    def __init__(self, percent = 100):
        self._percent = float(percent)

    def rezoom_on_resize(self):
        return False

    def get_page_screen_size(self, page_job, viewport_size):
        dpi = float(page_job.dpi)
        real_page_size = (page_job.width, page_job.height)
        screen_page_size = tuple(int(t * self._percent / dpi) for t in (real_page_size))
        return screen_page_size

    def _get_percent(self):
        return self._percent

class OneToOneZoom(Zoom):

    def rezoom_on_resize(self):
        return False

    def get_page_screen_size(self, page_job, viewport_size):
        real_page_size = (page_job.width, page_job.height)
        return real_page_size

class StretchZoom(Zoom):

    def rezoom_on_resize(self):
        return True

    def get_page_screen_size(self, page_job, viewport_size):
        return viewport_size

class FitWidthZoom(Zoom):

    def rezoom_on_resize(self):
        return True

    def get_page_screen_size(self, page_job, (viewport_width, viewport_height)):
        real_width, real_height = (page_job.width, page_job.height)
        ratio = 1.0 * real_height / real_width
        return (viewport_width, int(viewport_width * ratio))

class FitPageZoom(Zoom):

    def rezoom_on_resize(self):
        return True

    def get_page_screen_size(self, page_job, (viewport_width, viewport_height)):
        real_width, real_height  = (page_job.width, page_job.height)
        ratio = 1.0 * real_height / real_width
        screen_height = int(viewport_width * ratio)
        if screen_height <= viewport_height:
            screen_width = viewport_width
        else:
            screen_width = int(viewport_height / ratio)
            screen_height = viewport_height
        return (screen_width, screen_height)

class PageImage(wx.lib.ogl.RectangleShape):

    def __init__(self, widget, page_job, real_page_size, viewport_size, screen_page_size, xform_real_to_screen, render_mode, zoom):
        self._widget = widget
        self._render_mode = render_mode
        self._zoom = zoom
        self._screen_page_size = screen_page_size
        self._xform_real_to_screen = xform_real_to_screen
        self._page_job = page_job
        wx.lib.ogl.RectangleShape.__init__(self, *screen_page_size)
        self.SetX(self._width // 2)
        self.SetY(self._height // 2)

    def OnLeftClick(self, x, y, keys=0, attachment=0):
        shape = self.GetShape()
        canvas = shape.GetCanvas()
        dc = wx.ClientDC(canvas)
        canvas.PrepareDC(dc)
        to_deselect = list(shape for shape in canvas.GetDiagram().GetShapeList() if shape.Selected())
        for shape in to_deselect:
            shape.Select(False, dc)
        if to_deselect:
            canvas.Redraw(dc)
            shape.node.notify_deselect()
    
    def OnRightClick(self, x, y, keys=0, attachment=0):
        wx.CallAfter(lambda: self._widget.on_right_click((x, y), None))

    def OnDraw(self, dc):
        x, y, w, h = self.GetCanvas().GetUpdateRegion().GetBox()
        if w < 0 or h < 0 or x == y == w == h == 0:
            # This is not a regular refresh. 
            # So just see what might have been overwritten.
            x, y, w, h = dc.GetBoundingBox()
        dc.BeginDrawing()
        page_job = self._page_job
        xform_real_to_screen = self._xform_real_to_screen
        try:
            if page_job is None:
                raise decode.NotAvailable
            page_width, page_height = self._screen_page_size
            if x < 0:
                w += x
                x = 0
            if x >= page_width or w <= 0:
                raise decode.NotAvailable
            if x + w > page_width:
                w = page_width - x
            if y < 0:
                h += y
                y = 0
            if y >= page_height or h <= 0:
                raise decode.NotAvailable
            if y + h > page_height:
                h = page_height - y
            render_mode = self._render_mode
            if render_mode is None:
                raise decode.NotAvailable
            else:
                data = page_job.render(
                    render_mode,
                    (0, 0, page_width, page_height),
                    (x, y, w, h),
                    PIXEL_FORMAT,
                    1
                )
                image = wx.EmptyImage(w, h)
                image.SetData(data)
                dc.DrawBitmap(image.ConvertToBitmap(), x, y)
        except decode.NotAvailable, ex:
            dc.SetBrush(wx.WHITE_BRUSH)
            dc.SetPen(wx.TRANSPARENT_PEN)
            dc.DrawRectangle(x, y, w, h)
        dc.EndDrawing()

class NodeShape(wx.lib.ogl.RectangleShape):

    def _get_frame_color(self):
        raise NotImplementedError

    def _get_text(self):
        return None

    def __init__(self, node, has_text, xform_real_to_screen):
        wx.lib.ogl.RectangleShape.__init__(self, 100, 100)
        self._xform_real_to_screen = xform_real_to_screen
        self._node = node
        self._update_size()
        self._text_color = self._get_frame_color()
        self._text_pen = wx.Pen(self._text_color, 1)
        self.SetBrush(wx.TRANSPARENT_BRUSH)
        self._shows_text = has_text
        self._text = None
        if self._update_text() is not None:
            self._textMarginX = 1
            self._textMarginY = 1
            self.SetBrush(wx.WHITE_BRUSH)
        self.SetPen(self._text_pen)
        self.SetCentreResize(False)

    @property
    def node(self):
        return self._node

    def _update_size(self):
        x, y, w, h = self._xform_real_to_screen(self._node.rect)
        font = self.GetFont()
        if h <= 13:
            font_size = 8
        elif h <= 15:
            font_size = 9
        else:
            font_size = 10
        self.SetFont(wx.Font(font_size, wx.SWISS, wx.NORMAL, wx.NORMAL))
        self.SetSize(w, h)
        x, y = x + w // 2, y + h // 2
        self.SetX(x)
        self.SetY(y)

    def _update_text(self):
        self.ClearText()
        node = self._node
        if not self._shows_text:
            return
        text = self._text = self._get_text()
        if text is None:
            return
        self.AddText(text)
        return text

    def update(self):
        self._update_size()
        self._update_text()
        canvas = self.GetCanvas()
        canvas.Refresh() # FIXME: something lighter here?

    def _update_node_size(self):
        x, y, w, h = self.GetX(), self.GetY(), self.GetWidth(), self.GetHeight()
        screen_rect = x - w//2, y - h//2, w, h
        self._node.rect = self._xform_real_to_screen.inverse(screen_rect)

    def OnMovePost(self, dc, x, y, old_x, old_y, display):
        wx.lib.ogl.RectangleShape.OnMovePost(self, dc, x, y, old_x, old_y, display)
        self._update_node_size()

    def get_cdc(self):
        canvas = self.GetCanvas()
        dc = wx.ClientDC(canvas)
        canvas.PrepareDC(dc)
        return canvas, dc

    def deselect(self, notify = True, cdc = None):
        if not self.Selected():
            return
        try:
            canvas, dc = cdc
        except TypeError:
            canvas, dc = self.get_cdc()
        self.Select(False, dc)
        canvas.Redraw(dc)
        if notify:
            self.node.notify_deselect()

    def select(self, notify = True, cdc = None):
        if self.Selected():
            return
        try:
            canvas, dc = cdc
        except TypeError:
            canvas, dc = self.get_cdc()
        to_deselect = list(shape for shape in canvas.GetDiagram().GetShapeList() if shape.Selected())
        self.Select(True, dc)
        for shape in to_deselect:
            shape.Select(False, dc)
        if to_deselect:
            canvas.Redraw(dc)
        if notify:
            self.node.notify_select()

class PageTextCallback(models.text.PageTextCallback):

    def __init__(self, widget):
        self._widget = widget

    def notify_node_change(self, node):
        shape = self._widget._nonraster_shapes_map.get(node)
        if shape is not None:
            shape.update()

    def notify_node_select(self, node):
        self._widget.on_node_selected(node)

    def notify_node_deselect(self, node):
        self._widget.on_node_deselected(node)

    def notify_node_children_change(self, node):
        shape = self._widget._nonraster_shapes_map.get(node)
        if shape is not None:
            shape.deselect()
        self._widget.page = True
        # FIXME: consider something lighter here

    def notify_tree_change(self, node):
        self._widget.page = True

class TextShape(NodeShape):

    _FRAME_COLORS = \
    {
        djvu.const.TEXT_ZONE_COLUMN:    (0x80, 0x80, 0x00),
        djvu.const.TEXT_ZONE_REGION:    (0x80, 0x80, 0x80),
        djvu.const.TEXT_ZONE_PARAGRAPH: (0x80, 0x00, 0x00),
        djvu.const.TEXT_ZONE_LINE:      (0x80, 0x00, 0x80),
        djvu.const.TEXT_ZONE_WORD:      (0x00, 0x00, 0x80),
        djvu.const.TEXT_ZONE_CHARACTER: (0x00, 0x80, 0x00),
    }

    def _get_frame_color(self):
        return wx.Color(*self._FRAME_COLORS[self._node.type])

    def _get_text(self):
        if self._node.is_inner():
            return
        return self._node.text

class MapareaShape(NodeShape):

    def _get_frame_color(self):
        try:
            return self._node.border.color
        except AttributeError:
            return wx.BLUE

    def _get_text(self):
        return self._node.uri

class MapareaCallback(models.annotations.PageAnnotationsCallback):

    def __init__(self, widget):
        self._widget = widget

    def notify_node_change(self, node):
        shape = self._widget._nonraster_shapes_map.get(node)
        if shape is not None:
            shape.update()

    def notify_node_select(self, node):
        self._widget.on_node_selected(node)

    def notify_node_deselect(self, node):
        self._widget.on_node_deselected(node)
    
    def notify_node_delete(self, node):
        self._widget.page = True
        # FIXME: consider something lighter here

    def notify_node_add(self, node):
        self._widget.on_maparea_add(node)
    
    def notify_node_replace(self, node, other_node):
        self._widget.on_maparea_replace(node, other_node)

class ShapeEventHandler(wx.lib.ogl.ShapeEvtHandler):

    def __init__(self, widget):
        self._widget = widget
        wx.lib.ogl.ShapeEvtHandler.__init__(self)

    def OnLeftClick(self, x, y, keys=0, attachment=0):
        shape = self.GetShape()
        canvas = shape.GetCanvas()
        dc = wx.ClientDC(canvas)
        canvas.PrepareDC(dc)
        if shape.Selected():
            shape.deselect(notify = True)
        else:
            shape.select(notify = True)
    
    def OnRightClick(self, x, y, keys=0, attachment=0):
        shape = self.GetShape()
        wx.CallAfter(lambda: self._widget.on_right_click((x, y), shape.node))

class PageWidget(wx.lib.ogl.ShapeCanvas):

    _WXK_TO_LINK_GETTER = \
    {
        wx.WXK_LEFT:  lambda node: node.left_sibling,
        wx.WXK_RIGHT: lambda node: node.right_sibling,
        wx.WXK_UP:    lambda node: node.parent,
        wx.WXK_DOWN:  lambda node: node.left_child
    }

    def __init__(self, parent):
        wx.lib.ogl.ShapeCanvas.__init__(self, parent)
        self._initial_size = self.GetSize()
        self.SetBackgroundColour(wx.WHITE)
        self._diagram = wx.lib.ogl.Diagram()
        self._diagram.SetSnapToGrid(False)
        self.SetDiagram(self._diagram)
        self._diagram.SetCanvas(self)
        self._image = None
        dc = wx.ClientDC(self)
        self.PrepareDC(dc)
        self._render_mode = decode.RENDER_COLOR
        self._render_nonraster = None
        self.setup_nonraster_shapes()
        self._zoom = PercentZoom()
        self.page = None
        self._current_shape = None
        self.Bind(wx.EVT_CHAR, self.on_char)
    
    def OnMouseEvent(self, event):
        if event.GetEventType() == wx.wxEVT_MOUSEWHEEL:
            event.Skip()
            return
        wx.lib.ogl.ShapeCanvas.OnMouseEvent(self, event)

    def on_char(self, event):
        skip = True
        try:
            shape = self._current_shape
            if shape is None:
                return
            key_code = event.GetKeyCode()
            try:
                link_getter = self._WXK_TO_LINK_GETTER[key_code]
                next_node = link_getter(shape.node)
                next_shape = self._nonraster_shapes_map[next_node]
            except StopIteration:
                return
            except KeyError:
                if key_code == wx.WXK_DELETE:
                    wx.CallAfter(shape.node.delete)
                    skip = False
                return
            skip = False
        finally:
            if skip:
                event.Skip()
        def reselect():
            shape.deselect()
            next_shape.select()
        wx.CallAfter(reselect)
    
    def on_right_click(self, point, node):
        if self.render_nonraster == RENDER_NONRASTER_MAPAREA:
            self.show_maparea_menu(node, point)
    
    def show_maparea_menu(self, node, point, extra={}):
        origin = self._xform_real_to_screen.inverse(point)
        gui.maparea_menu.show_menu(self, self._page_annotations, node, point, origin)

    def on_node_selected(self, node):
        try:
            shape = self._nonraster_shapes_map[node]
        except KeyError:
            return
        return self._on_shape_selected(shape)

    def on_node_deselected(self, node):
        try:
            shape = self._nonraster_shapes_map[node]
        except KeyError:
            return
        return self._on_shape_deselected(shape)
    
    def on_maparea_add(self, node):
        self.page = True
        # TODO: something lighter

    def on_maparea_replace(self, node, other_node):
        if node not in self._nonraster_shapes_map:
            return
        self.page = True
        # TODO: something lighter

    def _on_shape_selected(self, shape):
        shape.select(notify = False) # in case it was selected otherwhere
        self._current_shape = shape

    def _on_shape_deselected(self, shape):
        shape.deselect(notify = False) # in case it was selected otherwhere
        self._current_shape = None

    def on_parent_resize(self, event):
        if self._zoom.rezoom_on_resize():
            self.zoom = self._zoom
        event.Skip()

    @apply
    def render_mode():
        def get(self):
            return self._render_mode
        def set(self, value):
            self._render_mode = value
            self.page = True
        return property(get, set)

    @apply
    def render_nonraster():
        def get(self):
            return self._render_nonraster
        def set(self, value):
            if value not in RENDER_NONRASTER_VALUES:
                raise ValueError
            self._render_nonraster = value
            self.setup_nonraster_shapes()
            self.recreate_shapes()
        return property(get, set)

    @apply
    def zoom():
        def get(self):
            return self._zoom
        def set(self, value):
            self._zoom = value
            self.page = True
        return property(get, set)

    @apply
    def page():
        def set(self, page):
            try:
                if page is None:
                    raise decode.NotAvailable
                elif page is True:
                    page_job = self._page_job
                    page_text = self._page_text
                    page_annotations = self._page_annotations
                    callbacks = self._callbacks
                else:
                    page_job = page.page_job
                    text_callback = PageTextCallback(self)
                    maparea_callback = MapareaCallback(self)
                    callbacks = text_callback, maparea_callback
                    page_text = page.text
                    page_text.register_callback(text_callback)
                    page_annotations = page.annotations
                    page_annotations.register_callback(maparea_callback)
                real_page_size = (page_job.width, page_job.height)
                viewport_size = tuple(self.GetParent().GetSize())
                screen_page_size = self._zoom.get_page_screen_size(page_job, viewport_size)
                screen_page_rect = (0, 0) + screen_page_size
                rotation = page_job.initial_rotation
                real_page_rect = (0, 0) + real_page_size
                xform_real_to_screen = decode.AffineTransform(real_page_rect, screen_page_rect)
                xform_real_to_screen.mirror_y()
                xform_rotate = decode.AffineTransform((0, 0, 1, 1), (0, 0, 1, 1))
                xform_rotate.rotate(rotation)
                text_page_rect = (0, 0) + xform_rotate(real_page_rect)[2:]
                xform_text_to_screen = decode.AffineTransform(text_page_rect, screen_page_rect)
                xform_text_to_screen.mirror_y()
                xform_text_to_screen.rotate(rotation)
                self.set_size(screen_page_size)
            except decode.NotAvailable:
                screen_page_size = -1, -1
                xform_real_to_screen = xform_text_to_screen = decode.AffineTransform((0, 0, 1, 1), (0, 0, 1, 1))
                page_job = None
                page_text = None
                page_annotations = None
                need_recreate_text = True
                callbacks = ()
            self._screen_page_size = screen_page_size
            self._xform_real_to_screen = xform_real_to_screen
            self._xform_text_to_screen = xform_text_to_screen
            self._page_job = page_job
            self._page_text = page_text
            self._page_annotations = page_annotations
            self._callbacks = callbacks
            if page is None:
                self.set_size(self._initial_size)
            if self._image is not None:
                self._image.Delete()
                self._image = None
            if page_job is not None:
                image = PageImage(self,
                    page_job = page_job,
                    real_page_size = real_page_size,
                    viewport_size = viewport_size,
                    screen_page_size = screen_page_size,
                    xform_real_to_screen = xform_real_to_screen,
                    render_mode = self.render_mode,
                    zoom = self.zoom)
                image.SetDraggable(False, False)
                self._image = image
            self.setup_nonraster_shapes()
            self.recreate_shapes()
        return property(fset = set)

    def recreate_shapes(self):
        self.remove_all_shapes()
        image = self._image
        if image is not None:
            self.add_shape(image)
        if self.render_nonraster is not None:
            for shape in self._nonraster_shapes:
                self.add_shape(shape)
                event_handler = ShapeEventHandler(self)
                event_handler.SetShape(shape)
                event_handler.SetPreviousHandler(shape.GetEventHandler())
                shape.SetEventHandler(event_handler)
        self.Refresh()

    def add_shape(self, shape):
        shape.SetCanvas(self)
        shape.Show(True)
        self._diagram.AddShape(shape)

    def remove_all_shapes(self):
        self._diagram.RemoveAllShapes()

    def set_size(self, size):
        if self.GetSize() == size:
            return
        self.SetSize(size)
        self.SetBestFittingSize(size)
        self.GetParent().Layout()
        self.GetParent().SetupScrolling()

    def setup_nonraster_shapes(self):
        self.clear_nonraster_shapes()
        have_text = self.render_mode is None
        if self.render_nonraster == RENDER_NONRASTER_TEXT and self._page_text is not None:
            self.setup_text_shapes(have_text)
        if self.render_nonraster == RENDER_NONRASTER_MAPAREA and self._page_annotations is not None:
            self.setup_maparea_shapes(have_text)

    def clear_nonraster_shapes(self):
        self._nonraster_shapes = ()
        self._nonraster_shapes_map = {}

    def setup_maparea_shapes(self, have_text = False):
        xform_real_to_screen = self._xform_real_to_screen
        try:
            items = \
            [
                (node, MapareaShape(node, have_text, xform_real_to_screen))
                for node in self._page_annotations.mapareas
            ]
            self._nonraster_shapes = tuple(shape for node, shape in items)
            self._nonraster_shapes_map = dict(items)
        except decode.NotAvailable, ex:
            pass

    def setup_text_shapes(self, have_text = False):
        xform_text_to_screen = self._xform_text_to_screen
        try:
            page_type = sexpr.Symbol('page')
            items = \
            [
                (node, TextShape(node, have_text, xform_text_to_screen))
                for node in self._page_text.get_preorder_nodes()
                if node is not None and node.type < djvu.const.TEXT_ZONE_PAGE
            ]
            self._nonraster_shapes = tuple(shape for node, shape in items)
            self._nonraster_shapes_map = dict(items)
        except decode.NotAvailable, ex:
            pass

__all__ = (
    'Zoom', 'PercentZoom', 'OneToOneZoom', 'StretchZoom', 'FitWidthZoom', 'FitPageZoom',
    'PageWidget',
    'RENDER_NONRASTER_TEXT', 'RENDER_NONRASTER_MAPAREA'
)

# vim:ts=4 sw=4 et
