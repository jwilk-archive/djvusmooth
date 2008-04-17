#!/usr/bin/python
# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>

import exceptions
import warnings
import weakref

class NotOverriddenWarning(exceptions.UserWarning):
	pass

def not_overridden(f):
	def new_f(self, *args, **kwargs):
		cls = type(self)
		warnings.warn(
			'`%s.%s.%s()` is not overriden' % (cls.__module__, cls.__name__, f.__name__),
			category = NotOverriddenWarning,
			stacklevel = 2
		)
		return f(self, *args, **kwargs)
	return new_f


def wref(obj):
	if obj is None:
		ref = weakref.ref(set())
		assert ref() is None
	else:
		ref = weakref.ref(object)
	return ref

# vim:ts=4 sw=4
