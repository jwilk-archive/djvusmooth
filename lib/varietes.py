# encoding=UTF-8
# Copyright © 2008, 2009 Jakub Wilk <jwilk@jwilk.net>
#
# This package is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 dated June, 1991.
#
# This package is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

import re
import functools
import warnings
import weakref

class NotOverriddenWarning(UserWarning):
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
    NotOverriddenWarning: `lib.varietes.B.f()` is not overridden
    >>> C().f(6, 7)
    42
    '''
    @functools.wraps(f)
    def new_f(self, *args, **kwargs):
        cls = type(self)
        warnings.warn(
            '`%s.%s.%s()` is not overridden' % (cls.__module__, cls.__name__, f.__name__),
            category = NotOverriddenWarning,
            stacklevel = 2
        )
        return f(self, *args, **kwargs)
    return new_f

def wref(o):
    r'''
    Return a weak reference to object. This is almost the same as
    `weakref.ref()`, but accepts `None` too.

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
    if o is None:
        ref = weakref.ref(set())
        assert ref() is None
    else:
        ref = weakref.ref(o)
    return ref

def indents_to_tree(lines):
    r'''
    >>> lines = [
    ... 'bacon',
    ... '   egg',
    ... '       eggs',
    ... 'ham',
    ... '   sausage',
    ... '   spam',
    ... '       bacon',
    ... '   egg'
    ... ]
    >>> indents_to_tree(lines)
    [None, ['bacon', ['egg', ['eggs']]], ['ham', ['sausage'], ['spam', ['bacon']], ['egg']]]

    '''
    root = [None]
    memo = [(-1, root)]
    for line in lines:
        old_len = len(line)
        line = line.lstrip()
        current = [line]
        indent = old_len - len(line)
        while memo[-1][0] >= indent:
            memo.pop()
        memo[-1][1].append(current)
        memo += (indent, current),
    return root

URI_SPECIAL_CHARACTERS = \
(
    ':/?#[]@' +    # RFC 3986, `gen-delims`
    '!$&()*+,;=' + # RFC 3986, `sub-delims`
    '%'            # RFC 3986, `pct-encoded`
)

def fix_uri(s):
    r'''
    >>> uri = 'http://eggs.spam/'
    >>> fix_uri(uri) == uri
    True
    >>> uri = fix_uri('http://eggs.spam/eggs and spam/')
    >>> uri
    'http://eggs.spam/eggs%20and%20spam/'
    >>> fix_uri(uri) == uri
    True
    '''
    from urllib import quote
    if isinstance(s, unicode):
        s = s.encode('UTF-8')
    return quote(s, safe=URI_SPECIAL_CHARACTERS)

replace_control_characters = re.compile('[\0-\x1f]+').sub

_is_html_color = re.compile('^[#][0-9a-fA-F]{6}$').match

def is_html_color(s):
    '''
    >>> is_html_color('#000000')
    True
    >>> is_html_color('#ffffff')
    True
    >>> is_html_color('#FFFFFF')
    True
    >>> is_html_color('#c0c0f0')
    True
    >>> is_html_color('')
    False
    >>> is_html_color('#bcdefg')
    False
    >>> is_html_color('#ffffff ')
    False
    >>> is_html_color(' #ffffff')
    False
    '''
    return bool(_is_html_color(s))

class idict(object):

    '''
    >>> o = idict(eggs = 'spam', ham = 'eggs')
    >>> o
    lib.varietes.idict(eggs='spam', ham='eggs')
    >>> o.eggs
    'spam'
    >>> o.ham
    'eggs'
    >>> o.spam
    Traceback (most recent call last):
    ...
    AttributeError: 'idict' object has no attribute 'spam'
    '''

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __repr__(self):
        return '%s.%s(%s)' % \
        (
            self.__module__,
            self.__class__.__name__,
            ', '.join('%s=%r' % (k, v) for k, v in self.__dict__.iteritems())
        )

# vim:ts=4 sw=4 et
