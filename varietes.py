#!/usr/bin/python
# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>

import exceptions
import warnings
import weakref
from cStringIO import StringIO

class NotOverriddenWarning(exceptions.UserWarning):
	pass

def not_overridden(f):
	r'''
	>>> warnings.filterwarnings('error', category=NotOverriddenWarning)
	>>> class B(object):
	...   @not_overridden
	...   def f(self, x, y): pass
	>>> class C(B):
	...   def f(self, x, y): return x * y
	>>> B().f(6, 7)
	Traceback (most recent call last):
	...
	NotOverriddenWarning: `varietes.B.f()` is not overriden
	>>> C().f(6, 7)
	42
	'''
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
	r'''
	>>> class O(object):
	...   pass
	>>> x = O()
	>>> xref = wref(x)
	>>> xref() is x
	True
	>>> del x
	>>> xref() is None
	True

	>>> xref = wref(None)
	>>> xref() is None
	True
	'''
	if obj is None:
		ref = weakref.ref(set())
		assert ref() is None
	else:
		ref = weakref.ref(obj)
	return ref

def untab(s, tab_stop = 8):
	r'''
	>>> untab('eggs')
	'eggs'
	>>> untab('e\tggs')
	'e       ggs'
	>>> untab('eg\tgs')
	'eg      gs'
	>>> untab('egg\ts')
	'egg     s'
	>>> untab('eggs\tham')
	'eggs    ham'
	>>> untab('eggs\t\tham')
	'eggs            ham'
	>>> untab('eggs\tham\teggs')
	'eggs    ham     eggs'
	'''
	tab_stop = int(tab_stop)
	if tab_stop < 1:
		raise ValueError('`tab_stop` must be >= 1')
	io = StringIO()
	try:
		cpos = -1
		start = 0
		while True:
			stop = s.find('\t', start)
			if stop < 0:
				break
			cpos -= stop - start
			io.write(buffer(s, start, stop - start))
			nspaces = cpos % tab_stop + 1
			cpos -= nspaces
			io.write(' ' * nspaces)
			start = stop + 1
		io.write(buffer(s, start, len(s) - start))
		return io.getvalue()
	finally:
		io.close()

# vim:ts=4 sw=4
