#!/usr/bin/python
# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>
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
*djvusmooth* is a graphical editor for `DjVu <http://djvu.org>`_ documents.
'''

import os
os.putenv('TAR_OPTIONS', '--owner root --group root --mode a+rX')

classifiers = '''\
Development Status :: 4 - Beta
Environment :: Console
Intended Audience :: End Users/Desktop
License :: OSI Approved :: GNU General Public License (GPL)
Operating System :: OS Independent
Programming Language :: Python
Programming Language :: Python :: 2
Topic :: Text Processing
Topic :: Multimedia :: Graphics\
'''.split('\n')

from distutils.core import setup
from lib import __version__

data_files = []
for root, dirs, files in os.walk('locale'):
    for f in files:
        if not f.endswith('.mo'):
            continue
        data_files.append(
            (os.path.join('share', root),
            [os.path.join(root, f)]
        ))

setup(
    name = 'djvusmooth',
    version = __version__,
    license = 'GNU GPL 2',
    description = 'graphical editor for DjVu',
    long_description = __doc__.strip(),
    classifiers = classifiers,
    url = 'http://jwilk.net/software/djvusmooth.html',
    author = 'Jakub Wilk',
    author_email = 'ubanus@users.sf.net',
    packages = ['djvusmooth'],
    package_dir = dict(djvusmooth='lib'),
    scripts = ['djvusmooth'],
    data_files = data_files,
)

# vim:ts=4 sw=4 et
