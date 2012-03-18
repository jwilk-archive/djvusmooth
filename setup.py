#!/usr/bin/python
# encoding=UTF-8
# Copyright © 2008, 2009, 2010, 2011 Jakub Wilk <jwilk@jwilk.net>
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

classifiers = '''
Development Status :: 4 - Beta
Environment :: Console
Intended Audience :: End Users/Desktop
License :: OSI Approved :: GNU General Public License (GPL)
Operating System :: OS Independent
Programming Language :: Python
Programming Language :: Python :: 2
Topic :: Text Processing
Topic :: Multimedia :: Graphics
'''.strip().split('\n')

import glob
import os

import distutils.core
from distutils.command.build import build as distutils_build
from distutils.command.sdist import sdist as distutils_sdist

from lib import __version__

data_files = []

if os.name == 'posix':
    data_files += [
        (os.path.join('share', 'applications'), ['extra/djvusmooth.desktop'])
    ]

class build_mo(distutils_build):

    description = 'build binary message catalogs'

    def run(self):
        if os.name != 'posix':
            return
        for poname in glob.glob(os.path.join('po', '*.po')):
            lang, _ = os.path.splitext(os.path.basename(poname))
            modir = os.path.join('locale', lang, 'LC_MESSAGES')
            if not os.path.isdir(modir):
                os.makedirs(modir)
            moname = os.path.join(modir, 'djvusmooth.mo')
            command = ['msgfmt', '-o', moname, '--check', '--check-accelerators', poname]
            self.make_file([poname], moname, distutils.spawn.spawn, [command])
            data_files.append((os.path.join('share', modir), [moname]))

class build_doc(distutils_build):

    description = 'build documentation'

    def run(self):
        if os.name != 'posix':
            return
        for xmlname in glob.glob(os.path.join('doc', '*.xml')):
            manname = os.path.splitext(xmlname)[0] + '.1'
            command = [
                'xsltproc', '--nonet',
                '--param', 'man.charmap.use.subset', '0',
                '--output', 'doc/',
                'http://docbook.sourceforge.net/release/xsl/current/manpages/docbook.xsl',
                xmlname,
            ]
            self.make_file([xmlname], manname, distutils.spawn.spawn, [command])
            data_files.append(('share/man/man1', [manname]))

distutils_build.sub_commands[:0] = [
    ('build_doc', None),
    ('build_mo', None)
]

class sdist(distutils_sdist):

    def run(self):
        self.run_command('build_doc')
        return distutils_sdist.run(self)

distutils.core.setup(
    name = 'djvusmooth',
    version = __version__,
    license = 'GNU GPL 2',
    description = 'graphical editor for DjVu',
    long_description = __doc__.strip(),
    classifiers = classifiers,
    url = 'http://jwilk.net/software/djvusmooth',
    author = 'Jakub Wilk',
    author_email = 'jwilk@jwilk.net',
    packages = ['djvusmooth'] + ['djvusmooth.%s' % x for x in 'gui models text'.split()],
    package_dir = dict(djvusmooth='lib'),
    scripts = ['djvusmooth'],
    data_files = data_files,
    cmdclass = dict(
        sdist=sdist,
        build_doc=build_doc,
        build_mo=build_mo,
    ),
)

# vim:ts=4 sw=4 et
