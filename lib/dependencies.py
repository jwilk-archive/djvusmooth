# encoding=UTF-8
# Copyright © 2008, 2009, 2010 Jakub Wilk <jwilk@jwilk.net>
#
# This package is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 dated June, 1991.
#
# This package is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

'''
Checks for djvusmooth dependencies.
'''

WX_VERSIONS = ('2.8-unicode', '2.6-unicode')
DDJVU_API_MIN_VERSION = 26
PYTHON_DJVULIBRE_MIN_VERSION = (0, 1, 4)

def _check_djvu():
    try:
        from djvu.decode import __version__ as djvu_decode_version
    except ImportError, ex:
        raise ImportError('%s; perhaps python-djvulibre is not installed' % (ex,))
    python_djvu_decode_version, ddjvu_api_version = djvu_decode_version.split('/')
    if int(ddjvu_api_version) < DDJVU_API_MIN_VERSION:
        raise ImportError('DjVuLibre with DDJVU API >= %d is required' % DDJVU_API_MIN_VERSION)
    python_djvu_decode_version = map(int, python_djvu_decode_version.split('.'))
    if tuple(python_djvu_decode_version) < PYTHON_DJVULIBRE_MIN_VERSION:
        raise ImportError('python-djvulibre >= %s is required' % ('.'.join(map(str, PYTHON_DJVULIBRE_MIN_VERSION))))

def _check_wx():
    try:
        import wxversion
    except ImportError, ex:
        raise ImportError('%s; perhaps wxPython is not installed' % (ex,))
    if not wxversion.checkInstalled(WX_VERSIONS):
        raise ImportError('wxPython 2.6 or 2.8 with Unicode support is required')
    wxversion.select(WX_VERSIONS)

def _check_xdg():
    try:
        from xdg import BaseDirectory
    except ImportError, ex:
        raise ImportError('%s; perhaps pyxdg is not installed' % (ex,))

try:
    _check_djvu()
finally:
    del _check_djvu
try:
    _check_wx()
finally:
    del _check_wx
try:
    _check_xdg()
finally:
    del _check_xdg

# vim:ts=4 sw=4 et
