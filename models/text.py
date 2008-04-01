#!/usr/bin/python
# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>

import djvu.sexpr

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
