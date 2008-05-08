# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>

'''
Checks for DjVuSmooth dependencies.
'''

def _check():
	from djvu.decode import __version__ as djvu_decode_version
	
	python_djvu_decode_version, ddjvu_api_version = djvu_decode_version.split('/')
	if int(ddjvu_api_version) < 26:
		raise ImportError('python-djvulibre with DDJVU API >= 26 is required')
	python_djvu_decode_version = map(int, python_djvu_decode_version.split('.'))
	if python_djvu_decode_version < [0, 1, 4]:
		raise ImportError('python-djvulibre >= 0.1.4 is required')

try:
	_check()
finally:
	del _check

# vim:ts=4 sw=4
