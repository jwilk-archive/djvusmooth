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

DDJVU_API_MIN_VERSION = 26
PYTHON_DJVULIBRE_MIN_VERSION = (0, 1, 4)

djvulibre_path = None

def _check_signals():
    # Protect from scanadf and possibly other software that sets SIGCHLD to
    # SIG_IGN.
    # https://bugs.debian.org/596232
    import os
    import signal
    if os.name == 'posix':
        signal.signal(signal.SIGCHLD, signal.SIG_DFL)

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
        from djvu.decode import __version__ as djvu_decode_version
    except ImportError as exc:
        raise ImportError('{exc}; perhaps python-djvulibre is not installed'.format(exc=exc))
    python_djvu_decode_version, ddjvu_api_version = djvu_decode_version.split('/')
    if int(ddjvu_api_version) < DDJVU_API_MIN_VERSION:
        raise ImportError('DjVuLibre with DDJVU API >= {ver} is required'.format(ver=DDJVU_API_MIN_VERSION))
    python_djvu_decode_version = map(int, python_djvu_decode_version.split('.'))
    if tuple(python_djvu_decode_version) < PYTHON_DJVULIBRE_MIN_VERSION:
        raise ImportError('python-djvulibre >= {ver} is required'.format(
            ver='.'.join(map(str, PYTHON_DJVULIBRE_MIN_VERSION))
        ))

def _check_wx():
    try:
        import wxversion
    except ImportError as exc:
        raise ImportError('{exc}; perhaps wxPython is not installed'.format(exc=exc))
    for ver in ['2.8-unicode', '3.0']:
        try:
            wxversion.select(ver, optionsRequired=True)
        except wxversion.VersionError:
            continue
        else:
            break
    else:
        raise ImportError('wxPython 3.0 or 2.8 in Unicode mode is required')

_check_signals()
_check_djvu()
_check_wx()

# vim:ts=4 sts=4 sw=4 et
