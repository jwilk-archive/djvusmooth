#!/usr/bin/python
# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>

import copy
import weakref
import itertools

import djvu.decode
import djvu.sexpr

from models import MultiPageModel

class Listener(object):
	pass

class Node(object):

	def __new__(cls, sexpr, owner):
		if len(sexpr) == 6 and isinstance(sexpr[5], djvu.sexpr.StringExpression):
			cls = LeafNode
		else:
			cls = InnerNode
		return object.__new__(cls, sexpr, owner)

	def __init__(self, sexpr, owner):
		self._owner = owner
		self._type = djvu.const.get_text_zone_type(sexpr[0].value)
		x0, y0, x1, y1 = (sexpr[i].value for i in xrange(1, 5))
		self._x = x0
		self._y = y0
		self._w = x1 - x0
		self._h = y1 - y0
	
	@property
	def sexpr(self):
		return self._construct_sexpr()
	
	def _construct_sexpr(self):
		raise NotImplementedError

	@apply
	def separator():
		def get(self):
			return djvu.const.TEXT_ZONE_SEPARATORS[self._type]
		return property(get)

	@apply
	def x():
		def get(self):
			return self._x
		def set(self, value):
			self._x = value
			self._notify_change()
		return property(get, set)

	@apply
	def y():
		def get(self):
			return self._y
		def set(self, value):
			self._y = value
			self._notify_change()
		return property(get, set)

	@apply
	def w():
		def get(self):
			return self._w
		def set(self, value):
			self._w = value
			self._notify_change()
		return property(get, set)

	@apply
	def h():
		def get(self):
			return self._h
		def set(self, value):
			self._h = value
			self._notify_change()
		return property(get, set)
	
	@apply
	def rect():
		def get(self):
			return self._x, self._y, self._w, self._h
		def set(self, value):
			self._x, self._y, self._w, self._h = value
			self._notify_change()
		return property(get, set)

	@apply
	def type():
		def get(self):
			return self._type
		return property(get)
	
	def strip(self, zone_type):
		raise NotImplementedError

	def _notify_change(self):
		return self._owner.notify_node_change(self)
	
class LeafNode(Node):

	def __init__(self, sexpr, owner):
		Node.__init__(self, sexpr, owner)
		self._text = sexpr[5].value.decode('UTF-8')

	def _construct_sexpr(self):
		x, y, w, h = self.x, self.y, self.w, self.h
		return djvu.sexpr.Expression((self.type, x, y, x + w, y + h, self.text))

	@apply
	def text():
		def get(self):
			return self._text
		def set(self, value):
			self._text = value
			self._notify_change()
		return property(get, set)

	def strip(self, zone_type):
		if self.type <= zone_type:
			return self.text, self.separator
		return self
	
	def __getitem__(self, n):
		raise TypeError
	
	def __len__(self):
		raise TypeError

	def __iter__(self):
		raise TypeError

class InnerNode(Node):

	def __init__(self, sexpr, owner):
		Node.__init__(self, sexpr, owner)
		self._children = [Node(child, self._owner) for child in sexpr[5:]]

	def _construct_sexpr(self):
		x, y, w, h = self.x, self.y, self.w, self.h
		return djvu.sexpr.Expression(
			itertools.chain(
				(self.type, x, y, x + w, y + h),
				(child.sexpr for child in self)
			)
		)

	@apply
	def text():
		return property()

	def strip(self, zone_type):
		stripped_children = [child.strip(zone_type) for child in self._children]
		if self.type <= zone_type:
			texts = [text for text, child_separator in stripped_children]
			return child_separator.join(texts), self.separator
		else:
			node_children = [child for child in stripped_children if isinstance(child, Node)]
			if node_children:
				self._children = node_children
				return self
			else:
				texts = [text for text, child_separator in stripped_children]
				text = child_separator.join(texts)
				return Node(
					djvu.sexpr.Expression((
						self.type,
						self.x, self.y,
						self.x + self.w, self.y + self.h,
						text
					)), self._owner
				)
		return self
	
	def __getitem__(self, n):
		return self._children[n]
	
	def __len__(self):
		return len(self._children)

	def __iter__(self):
		return iter(self._children)

class Text(MultiPageModel):

	def get_page_model_class(self, n):
		return PageText

class PageTextCallback(object):

	def notify_node_change(self, node):
		raise NotImplementedError(self)

	def notify_tree_change(self, node):
		raise NotImplementedError(self)

class PageText(object):

	def __init__(self, n, original_data):
		self._callbacks = weakref.WeakKeyDictionary()
		self._original_sexpr = original_data
		self.revert()
		self._n = n
	
	def register_callback(self, callback):
		if not isinstance(callback, PageTextCallback):
			raise TypeError
		self._callbacks[callback] = 1

	@apply
	def root():
		def get(self):
			return self._root
		return property(get)
	
	@apply
	def raw_value():
		def get(self):
			return self._root.sexpr
		def set(self, sexpr):
			self._sexpr = sexpr
			self._root = Node(self._sexpr, self)
			self.notify_tree_change()
		return property(get, set)

	def strip(self, zone_type):
		zone_type = djvu.const.get_text_zone_type(zone_type) # ensure it's not a plain Symbol
		self._root = self._root.strip(zone_type)
		self.notify_tree_change()

	def clone(self):
		from copy import copy
		return copy(self)
	
	def export(self, djvused):
		djvused.select(self._n + 1)
		djvused.set_text(self.raw_value)
	
	def revert(self):
		self.raw_value = copy.deepcopy(self._original_sexpr)
		self._dirty = False
	
	def is_dirty(self):
		return self._dirty
	
	def notify_node_change(self, node):
		self._dirty = True
		for callback in self._callbacks:
			callback.notify_node_change(node)
	
	def notify_tree_change(self):
		self._dirty = True
		for callback in self._callbacks:
			callback.notify_tree_change(self._root)
	
	def get_preorder_nodes(self):
		return _get_preorder_nodes(self.root)

	def get_postorder_nodes(self):
		return _get_postorder_nodes(self.root)

	def get_leafs(self):
		return _get_leafs(self.root)
	
def _get_preorder_nodes(node):
	yield node
	if isinstance(node, LeafNode):
		return
	for child in node:
		for item in _get_preorder_nodes(child):
			yield item

def _get_postorder_nodes(node):
	if isinstance(node, InnerNode):
		for child in node:
			for item in _get_postorder_nodes(child):
				yield item
	yield node

def _get_leafs(node):
	if isinstance(node, LeafNode):
		yield node
	else:
		for child in node:
			for item in _get_leafs(child):
				yield item

__all__ = 'Text', 'PageText'

# vim:ts=4 sw=4
