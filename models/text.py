#!/usr/bin/python
# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>

import copy
import weakref

import djvu.sexpr

from models import MultiPageModel

class ExpressionProxy(object):

	def __new__(cls, sexpr, owner):
		if isinstance(sexpr, djvu.sexpr.ListExpression):
			return object.__new__(ListExpressionProxy, sexpr, owner)
		else:
			return sexpr

class ListExpressionProxy(ExpressionProxy):
	
	def __init__(self, sexpr, owner):
		if not isinstance(sexpr, djvu.sexpr.ListExpression):
			raise TypeError
		self._sexpr = sexpr
		self._owner = owner

	def __len__(self):
		return len(self._sexpr)
	
	def __nonzero__(self):
		return bool(self._sexpr)
	
	def __iter__(self):
		return (ExpressionProxy(item, self._owner) for item in self._sexpr)

	def __getitem__(self, key):
		return ExpressionProxy(self._sexpr[key], self._owner)
	
	def __setitem__(self, key, value):
		if isinstance(value, ListExpressionProxy):
			value = value._sexpr
		self._sexpr[key] = value
		self._owner.notify(self)

class Text(MultiPageModel):

	def get_page_model_class(self, n):
		return PageText
	
class PageText(object):

	def __init__(self, n, original_data):
		self._original_sexpr = original_data
		self.revert()
		self._n = n
		self._callbacks = weakref.WeakKeyDictionary()
	
	def register_callback(self, callback):
		self._callbacks[callback] = 1

	@apply
	def value():
		def get(self):
			return self._proxy
		def set(self, value):
			self._proxy = ExpressionProxy(value, self)
			self._dirty = True
		return property(get, set)
	
	@apply
	def raw_value():
		def get(self):
			return self._proxy._sexpr
		return property(get)
	
	def clone(self):
		from copy import copy
		return copy(self)
	
	def export(self, djvused):
		djvused.select(self._n + 1)
		djvused.set_text(self.raw_value)
	
	def revert(self):
		self._proxy = ExpressionProxy(copy.deepcopy(self._original_sexpr), self)
		self._dirty = False
	
	def is_dirty(self):
		return self._dirty
	
	def notify(self, sexpr):
		self._dirty = True
		for callback in self._callbacks:
			callback()
	
def extract_text(sexpr):
	if len(sexpr) < 5:
		pass # should not happen
	elif len(sexpr) == 6 and isinstance(sexpr[5], djvu.sexpr.StringExpression):
		yield tuple(sexpr[i].value for i in xrange(1, 5)), sexpr[5].value
	else:
		for subexpr in sexpr[5:]:
			for item in extract_text(subexpr):
				yield item


__all__ = 'Text', 'PageText', 'extract_text'

# vim:ts=4 sw=4
