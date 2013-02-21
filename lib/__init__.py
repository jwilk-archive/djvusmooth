__version__ = '0.2.15'
__author__ = 'Jakub Wilk <jwilk@jwilk.net>'

import sys

if sys.version_info < (2, 5):
    raise RuntimeError('Python >= 2.5 is required')
if sys.version_info >= (3, 0):
    raise RuntimeError('Python 2.X is required')

# vim:ts=4 sw=4 et
