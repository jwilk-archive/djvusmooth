import sys

if sys.version_info < (2, 7):
    raise RuntimeError('Python >= 2.7 is required')
if sys.version_info >= (3, 0):
    raise RuntimeError('Python 2.X is required')

__version__ = '0.3.1'
__author__ = 'Jakub Wilk <jwilk@jwilk.net>'

# vim:ts=4 sts=4 sw=4 et
