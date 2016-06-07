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
*djvusmooth* is a graphical editor for `DjVu <http://djvu.org>`_ documents.
'''

from __future__ import with_statement
# Let's keep this __future__ import here, even though Python 2.5 is no longer
# supported, so that people running setup.py against the unsupported version
# get a nice error message instead of SyntaxError.

classifiers = '''
Development Status :: 4 - Beta
Environment :: Console
Intended Audience :: End Users/Desktop
License :: OSI Approved :: GNU General Public License (GPL)
Operating System :: OS Independent
Programming Language :: Python
Programming Language :: Python :: 2
Programming Language :: Python :: 2.6
Programming Language :: Python :: 2.7
Topic :: Text Processing
Topic :: Multimedia :: Graphics
'''.strip().splitlines()

import glob
import os
import re

import distutils.core
import distutils.errors
from distutils.command.build import build as distutils_build
from distutils.command.clean import clean as distutils_clean
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
        for poname in glob.iglob(os.path.join('po', '*.po')):
            lang, _ = os.path.splitext(os.path.basename(poname))
            modir = os.path.join('locale', lang, 'LC_MESSAGES')
            if not os.path.isdir(modir):
                os.makedirs(modir)
            moname = os.path.join(modir, 'djvusmooth.mo')
            command = ['msgfmt', '-o', moname, '--verbose', '--check', '--check-accelerators', poname]
            self.make_file([poname], moname, distutils.spawn.spawn, [command])
            data_files.append((os.path.join('share', modir), [moname]))

class check_po(distutils_build):

    description = 'perform some checks on message catalogs'

    def run(self):
        for poname in glob.iglob(os.path.join('po', '*.po')):
            checkname = poname + '.sdist-check'
            with open(checkname, 'w'):
                pass
            try:
                for feature in 'untranslated', 'fuzzy':
                    with open(checkname, 'w'):
                        pass
                    command = ['msgattrib', '--' + feature, '-o', checkname, poname]
                    distutils.spawn.spawn(command)
                    with open(checkname) as file:
                        entries = file.read()
                    if entries:
                        raise IOError(None, '{po} has {n} entries'.format(po=poname, n=feature))
            finally:
                os.unlink(checkname)

class build_doc(distutils_build):

    description = 'build documentation'

    _url_regex = re.compile(
        r'^(\\%https?://.*)',
        re.MULTILINE
    )

    _date_regex = re.compile(
        '"(?P<month>[0-9]{2})/(?P<day>[0-9]{2})/(?P<year>[0-9]{4})"'
    )

    def build_man(self, manname, commandline):
        self.spawn(commandline)
        with open(manname, 'r+') as file:
            contents = file.read()
            # Format URLs:
            contents = self._url_regex.sub(
                lambda m: r'\m[blue]\fI{0}\fR\m[]'.format(*m.groups()),
                contents,
            )
            # Use RFC 3339 date format:
            contents = self._date_regex.sub(
                lambda m: r'{year}\-{month}\-{day}'.format(**m.groupdict()),
                contents
            )
            file.seek(0)
            file.truncate()
            file.write(contents)

    def run(self):
        if os.name != 'posix':
            return
        for xmlname in glob.iglob(os.path.join('doc', '*.xml')):
            manname = os.path.splitext(xmlname)[0] + '.1'
            command = [
                'xsltproc', '--nonet',
                '--param', 'man.authors.section.enabled', '0',
                '--param', 'man.charmap.use.subset', '0',
                '--param', 'man.font.links', '"I"',
                '--output', 'doc/',
                'http://docbook.sourceforge.net/release/xsl/current/manpages/docbook.xsl',
                xmlname,
            ]
            self.make_file([xmlname], manname, self.build_man, [manname, command])
            data_files.append(('share/man/man1', [manname]))

distutils_build.sub_commands[:0] = [
    ('build_doc', None),
    ('build_mo', None)
]

class clean(distutils_clean):

    def run(self):
        distutils_clean.run(self)
        if not self.all:
            return
        for manname in glob.iglob(os.path.join('doc', '*.1')):
            with open(manname, 'r') as file:
                stamp = file.readline()
            if stamp != sdist.manpage_stamp:
                self.execute(os.unlink, [manname], 'removing {0}'.format(manname))

class sdist(distutils_sdist):

    manpage_stamp = '''.\\" [created by setup.py sdist]\n'''

    def run(self):
        self.run_command('build_doc')
        self.run_command('check_po')
        self.run_command('build_mo')
        return distutils_sdist.run(self)

    def _rewrite_manpage(self, manname):
        with open(manname, 'r') as file:
            contents = file.read()
        os.unlink(manname)
        with open(manname, 'w') as file:
            file.write(self.manpage_stamp)
            file.write(contents)

    def make_release_tree(self, base_dir, files):
        distutils_sdist.make_release_tree(self, base_dir, files)
        for manname in glob.iglob(os.path.join(base_dir, 'doc', '*.1')):
            self.execute(self._rewrite_manpage, [manname], 'rewriting {0}'.format(manname))

distutils.core.setup(
    name='djvusmooth',
    version=__version__,
    license='GNU GPL 2',
    description='graphical editor for DjVu',
    long_description=__doc__.strip(),
    classifiers=classifiers,
    url='http://jwilk.net/software/djvusmooth',
    author='Jakub Wilk',
    author_email='jwilk@jwilk.net',
    packages=(
        ['djvusmooth'] +
        ['djvusmooth.{mod}'.format(mod=mod) for mod in ['gui', 'models', 'text']]
    ),
    package_dir=dict(djvusmooth='lib'),
    scripts=['djvusmooth'],
    data_files=data_files,
    cmdclass=dict(
        build_doc=build_doc,
        build_mo=build_mo,
        check_po=check_po,
        clean=clean,
        sdist=sdist,
    ),
)

# vim:ts=4 sts=4 sw=4 et
