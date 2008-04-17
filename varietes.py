#!/usr/bin/python
# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>

import exceptions
import warnings

class NotOverridenWarning(exceptions.UserWarning):
	pass

def not_overridden(f):
	def new_f(self, *args, **kwargs):
		warnings.warn('%r is not overriden', category=NotOverriddenWarning)
		return f(*args, **kwargs)
	return new_f

# vim:ts=4 sw=4
