#!/usr/bin/python
# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>

import djvu.sexpr

from models import MultiPageModel

class Text(MultiPageModel):

	def get_page_model_class(self, n):
		return PageText

class PageText(object):

	def __init__(self, n, original_data):
		self._sexpr = self._original_sexpr = original_data
		self._dirty = False
		self._n = n

	@apply
	def value():
		def get(self):
			return self._sexpr
		def set(self, value):
			self._sexpr = value
			self._dirty = True
		return property(get, set)
	
	def clone(self):
		from copy import copy
		return copy(self)
	
	def export(self, djvused):
		djvused.select(self._n + 1)
		djvused.set_text(self._sexpr)
	
	def revert(self):
		self._sexpr = self._original_sexpr
		self._dirty = False
	
	def is_dirty(self):
		return self._dirty
	
def extract_text(sexpr):
	if len(sexpr) < 5:
		pass # should not happen
	elif len(sexpr) == 6 and isinstance(sexpr[5], djvu.sexpr.StringExpression):
		yield tuple(sexpr[i].value for i in xrange(1, 5)), sexpr[5].value
	else:
		for subexpr in sexpr[5:]:
			for item in extract_text(subexpr):
				yield item

# vim:ts=4 sw=4
