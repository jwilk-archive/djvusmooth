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

import os.path
import subprocess
import tempfile

class temporary_file(object):

    def __init__(self, suffix='', prefix='djvusmooth.', dir=None, text=False):
        fd, self.name = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=dir, text=text)
        self.mode = 'r+' + 'bt'[bool(text)]
        self.fp = os.fdopen(fd, self.mode)

    def _reopen(self):
        if self.fp is None:
            self.fp = open(self.name, self.mode)

    def flush(self):
        if self.fp is None:
            return
        self.fp.close()
        self.fp = None

    def close(self):
        if self.name is None:
            return
        self.flush()
        os.remove(self.name)
        self.name = None

    def seek(self, offset, whence=0):
        self._reopen()
        self.fp.seek(offset, whence)

    def write(self, s):
        self._reopen()
        self.fp.write(s)

    def read(self, n=-1):
        self._reopen()
        return self.fp.read(n)

    def __iter__(self):
        self._reopen()
        return iter(self.fp)

    def __enter__(self):
        return self

    def __exit__(self, exc, value, tb):
        self.close()

class Editor(object):

    def __call__(self, path):
        raise NotImplementedError

class RunMailcapEditor(object):

    def __call__(self, path):
        path = os.path.abspath(path)
        edit = subprocess.Popen(
            ['edit', 'text/plain:{path}'.format(path=path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        edit.stdin.close()
        edit.stdout.close()
        edit.wait()

class CustomEditor(object):

    def __init__(self, command, *extra_args):
        self._command = [command]
        self._command += extra_args

    def __call__(self, path):
        path = os.path.abspath(path)
        edit = subprocess.Popen(
            self._command + [path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        edit.stdin.close()
        edit.stdout.close()
        edit.wait()

# vim:ts=4 sts=4 sw=4 et
