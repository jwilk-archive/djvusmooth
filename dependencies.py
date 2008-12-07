# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>

'''
Checks for DjVuSmooth dependencies.
'''

WX_VERSION = '2.6-unicode'
DDJVU_API_MIN_VERSION = 26
PYTHON_DJVULIBRE_MIN_VERSION = (0, 1, 4)

def _check_djvu():
    from djvu.decode import __version__ as djvu_decode_version
    
    python_djvu_decode_version, ddjvu_api_version = djvu_decode_version.split('/')
    if int(ddjvu_api_version) < DDJVU_API_MIN_VERSION:
        raise ImportError('python-djvulibre with DDJVU API >= %d is required' % DDJVU_API_MIN_VERSION)
    python_djvu_decode_version = map(int, python_djvu_decode_version.split('.'))
    if tuple(python_djvu_decode_version) < PYTHON_DJVULIBRE_MIN_VERSION:
        raise ImportError('python-djvulibre >= %s is required' % ('.'.join(map(str, PYTHON_DJVULIBRE_MIN_VERSION))))

def _check_wx():
    import wxversion
    if not wxversion.checkInstalled(WX_VERSION):
        raise ImportError('wxPython 2.6 with unicode support is required')
    wxversion.select(WX_VERSION)

try:
    _check_djvu()
finally:
    del _check_djvu
try:
    _check_wx()
finally:
    del _check_wx

# vim:ts=4 sw=4 et
