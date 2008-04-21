#!/usr/bin/python
# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>

import weakref
import itertools

import djvu.sexpr
import djvu.const

from varietes import not_overridden, wref, fix_uri, indents_to_tree

class Node(object):

	def __init__(self, sexpr, owner):
		self._owner = owner
		self._type = None

	def _set_children(self, children):
		self._children = list(children)
		prev = None
		for child in self._children:
			child._link_left = wref(prev)
			child._link_parent = wref(self)
			prev = child
		prev = None
		for child in reversed(self._children):
			child._link_right = wref(prev)
			prev = child

	def add_child(self, node):
		self._children
		if self._children:
			self._children[-1]._link_ref = wref(node)
			node._link_right = wref(self._children[-1])
		node._link_parent = wref(self)
		self._children += node,
		self._notify_children_change()

	def remove_child(self, child):
		child_idx = self._children.index(child)
		if child_idx - 1 >= 0:
			self._children[child_idx - 1]._link_right = child._link_right
		if child_idx + 1 < len(self._children):
			self._children[child_idx + 1]._link_left = child._link_left
		child._link_left = child._link_right = child._link_parent = wref(None)
		del self._children[child_idx]
		self._notify_children_change()
	
	uri = property()
	text = property()

	@property
	def sexpr(self):
		return self._construct_sexpr()

	def _construct_sexpr(self):
		raise NotImplementedError

	@property
	def type(self):
		return self._type

	def __getitem__(self, item):
		return self._children[item]
	
	def __len__(self):
		return len(self._children)

	def __iter__(self):
		return iter(self._children)

	left_sibling = property()
	right_sibling = property()
	parent = property()

	@apply
	def left_child():
		def get(self):
			return iter(self).next()
		return property(get)
	
	def delete(self):
		raise NotImplementedError

	def _notify_children_change(self):
		return self._owner.notify_node_children_change(self)
	
class RootNode(Node):

	def __init__(self, sexpr, owner):
		Node.__init__(self, sexpr, owner)
		sexpr = iter(sexpr)
		self._type = sexpr.next().value
		self._set_children(InnerNode(subexpr, owner) for subexpr in sexpr)
	
	def _construct_sexpr(self):
		return djvu.sexpr.Expression(itertools.chain(
			(self.type,),
			(child._construct_sexpr() for child in self._children)
		))

	def export_as_plaintext(self, stream):
		for child in self:
			child.export_as_plaintext(stream, indent=0)

class InnerNode(Node):

	def __init__(self, sexpr, owner):
		Node.__init__(self, sexpr, owner)
		sexpr = iter(sexpr)
		self._text = sexpr.next().value
		self._uri = fix_uri(sexpr.next().value)
		self._set_children(InnerNode(subexpr, owner) for subexpr in sexpr)

	def _construct_sexpr(self):
		return djvu.sexpr.Expression(itertools.chain(
			(self.text, self.uri),
			(child._construct_sexpr() for child in self._children)
		))

	@apply
	def uri():
		def get(self):
			return self._uri
		def set(self, value):
			self._uri = value
			self._notify_change()
		return property(get, set)
		
	@apply
	def text():
		def get(self):
			return self._text
		def set(self, value):
			self._text = value
			self._notify_change()
		return property(get, set)
	
	def _notify_change(self):
		self._owner.notify_node_change(self)

	def notify_select(self):
		self._owner.notify_node_select(self)
	
	def export_as_plaintext(self, stream, indent):
		stream.write('    ' * indent)
		stream.write(self.uri)
		stream.write(' ')
		stream.write(self.text) # TODO: what about control characters etc.?
		stream.write('\n')
		for child in self:
			child.export_as_plaintext(stream, indent = indent + 1)

	@apply
	def left_sibling():
		def get(self):
			link = self._link_left()
			if link is None:
				raise StopIteration
			return link
		return property(get)

	@apply
	def right_sibling():
		def get(self):
			link = self._link_right()
			if link is None:
				raise StopIteration
			return link
		return property(get)

	@apply
	def parent():
		def get(self):
			link = self._link_parent()
			if link is None:
				raise StopIteration
			return link
		return property(get)

	def delete(self):
		try:
			parent = self.parent
		except StopIteration:
			return
		parent.remove_child(self)

class OutlineCallback(object):

	@not_overridden
	def notify_tree_change(self, node):
		pass

	@not_overridden
	def notify_node_change(self, node):
		pass

	@not_overridden
	def notify_node_children_change(self, node):
		pass
	
	@not_overridden
	def notify_node_select(self, node):
		pass

class Outline(object):

	def __init__(self):
		self._callbacks = weakref.WeakKeyDictionary()
		self._original_sexpr = self.acquire_data()
		self.revert()

	def register_callback(self, callback):
		if not isinstance(callback, OutlineCallback):
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
			if not sexpr:
				sexpr = djvu.const.EMPTY_OUTLINE
			self._root = RootNode(sexpr, self)
			self.notify_tree_change()
		return property(get, set)
	
	def remove(self):
		self.raw_value = djvu.const.EMPTY_OUTLINE

	def revert(self):
		self.raw_value = self._original_sexpr
		self._dirty = False

	def acquire_data(self):
		return djvu.const.EMPTY_OUTLINE

	def notify_tree_change(self):
		self._dirty = True
		for callback in self._callbacks:
			callback.notify_tree_change(self._root)

	def notify_node_change(self, node):
		self._dirty = True
		for callback in self._callbacks:
			callback.notify_node_change(node)

	def notify_node_children_change(self, node):
		self._dirty = True
		for callback in self._callbacks:
			callback.notify_node_children_change(node)

	def notify_node_select(self, node):
		for callback in self._callbacks:
			callback.notify_node_select(node)
	
	def export(self, djvused):
		if self.root:
			value = self.raw_value
		else:
			value = None
		djvused.set_outline(value)
	
	def export_as_plaintext(self, stream):
		return self.root.export_as_plaintext(stream)
	
	def import_plaintext(self, lines):
		def fix_node(node):
			it = iter(node)
			it.next()
			for subnode in it:
				fix_node(subnode)
			text = node[0]
			if text is not None:
				node[0:1] = (text.split(None, 1) + ['', ''])[1::-1]
		tree = indents_to_tree(lines)
		fix_node(tree)
		tree[0:1] = djvu.const.EMPTY_OUTLINE
		self.raw_value = djvu.sexpr.Expression(tree)

# vim:ts=4 sw=4
