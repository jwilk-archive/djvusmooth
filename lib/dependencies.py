# encoding=UTF-8

# Copyright © 2008-2015 Jakub Wilk <jwilk@jwilk.net>
#
# This file is part of djvusmooth.
#
# djvusmooth is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# djvusmooth is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
# more details.

'''
Checks for djvusmooth dependencies.
'''

djvulibre_path = None

def _check_djvu():
    # On Windows, special measures may be needed to find the DjVuLibre DLL.
    global djvulibre_path
    try:
        from djvu.dllpath import set_dll_search_path
    except ImportError:
        pass
    else:
        djvulibre_path = set_dll_search_path()
    try:
        import djvu.decode
    except ImportError as exc:
        raise ImportError('{exc}; is python-djvulibre installed?'.format(exc=exc))
    del djvu  # quieten pyflakes

def _check_wx():
    try:
        import wxversion
    except ImportError as exc:
        raise ImportError('{exc}; is wxPython installed?'.format(exc=exc))
    for ver in ['2.8-unicode', '3.0']:
        try:
            wxversion.select(ver, optionsRequired=True)
        except wxversion.VersionError:
            continue
        else:
            break
    else:
        raise ImportError('wxPython 3.0 or 2.8 in Unicode mode is required')

_check_djvu()
_check_wx()

# vim:ts=4 sts=4 sw=4 et
