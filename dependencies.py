# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>

'''
Checks for DjVuSmooth dependencies.
'''

WX_VERSION = '2.6-unicode'

def _check_djvu():
	from djvu.decode import __version__ as djvu_decode_version
	
	python_djvu_decode_version, ddjvu_api_version = djvu_decode_version.split('/')
	if int(ddjvu_api_version) < 26:
		raise ImportError('python-djvulibre with DDJVU API >= 26 is required')
	python_djvu_decode_version = map(int, python_djvu_decode_version.split('.'))
	if python_djvu_decode_version < [0, 1, 4]:
		raise ImportError('python-djvulibre >= 0.1.4 is required')

def _check_wx():
	import wxversion
	WX_VERSION
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

# vim:ts=4 sw=4
