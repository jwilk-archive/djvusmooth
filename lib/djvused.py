# encoding=UTF-8

# Copyright © 2008-2015 Jakub Wilk <jwilk@jwilk.net>
#
# This package is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 dated June, 1991.
#
# This package is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

import os.path
import subprocess
import threading

from djvu.sexpr import Expression, Symbol

djvused_path = None
if os.name =='nt':
    from . import dependencies
    djvused_path = os.path.join(dependencies.djvulibre_path, 'djvused.exe')
else:
    from . import pkgconfig
    try:
        djvulibre_bin_path = os.path.join(pkgconfig.Package('ddjvuapi').variable('exec_prefix'), 'bin')
    except (IOError, OSError):
        pass
    else:
        djvused_path = os.path.join(djvulibre_bin_path, 'djvused')
if djvused_path is None or not os.path.isfile(djvused_path):
    # Let's hope it's within $PATH...
    djvused_path = 'djvused'

def _djvused_usability_check():
    try:
        djvused = subprocess.Popen([djvused_path], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        djvused.communicate()
        if djvused.returncode == 10:
            return
    except (IOError, OSError):
        pass
    raise IOError('{path!r} does not seem to be usable'.format(path=djvused_path))

_djvused_usability_check()

class IOError(IOError):
    pass

class StreamEditor(object):

    def __init__(self, file_name, autosave = False):
        self._file_name = file_name
        self._commands = []
        self._autosave = autosave

    def clone(self):
        return StreamEditor(self._filename, self._autosave)

    def _add(self, *commands):
        for command in commands:
            if not isinstance(command, str):
                raise TypeError
        self._commands += commands

    def select_all(self):
        self._add('select')

    def select(self, page_id):
        self._add('select %s' % page_id)

    def select_shared_annotations(self):
        self._add('select-shared-ant')

    def create_shared_annotations(self):
        self._add('create-shared-ant')

    def set_annotations(self, annotations):
        self._add('set-ant')
        for annotation in annotations:
            self._add(str(annotation))
        self._add('.')

    def remove_annotations(self):
        self._add('remove-ant')

    def print_annotations(self):
        self._add('print-ant')

    def set_metadata(self, meta):
        self._add('set-meta')
        for key, value in meta.iteritems():
            value = unicode(value)
            self._add('%s\t%s' % (Expression(Symbol(key)), Expression(value)))
        self._add('.')

    def remove_metadata(self):
        self._add('remove-meta')

    def set_text(self, text):
        if text is None:
            self.remove_text()
        else:
            self._add('set-txt', str(text), '.')

    def remove_text(self):
        self._add('remove-txt')

    def set_outline(self, outline):
        if outline is None:
            outline = ''
        self._add('set-outline', str(outline), '.')

    def set_thumbnails(self, size):
        self._add('set-thumbnails %d' % size)

    def remove_thumbnails(self):
        self._add('remove-thumbnails')

    def set_page_title(self, title):
        self._add('set-page-title %s' % Expression(title))

    def save_page(self, file_name, include = False):
        command = 'save-page'
        if include:
            command += '-with'
        self._add('%s %s' % command, file_name)

    def save_as_bundled(self, file_name):
        self._add('save-bundled %s' % file_name)

    def save_as_indirect(self, file_name):
        self._add('save-indirect %s' % file_name)

    def save(self):
        self._add('save')

    def _reader_thread(self, fo, result):
        result[0] = fo.read(),

    def _execute(self, commands, save = False):
        args = [djvused_path]
        if save:
            args += '-s',
        args += self._file_name,
        djvused = subprocess.Popen(args, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        result = [None]
        reader_thread = threading.Thread(target = self._reader_thread, args = (djvused.stdout, result))
        reader_thread.setDaemon(True)
        reader_thread.start()
        stdin = djvused.stdin
        for command in commands:
            stdin.write(command + '\n')
        stdin.close()
        djvused.wait()
        if djvused.returncode:
            raise IOError(djvused.stderr.readline().lstrip('* '))
        reader_thread.join()
        return result[0]

    def commit(self):
        try:
            return self._execute(self._commands, save = self._autosave)
        finally:
            self._commands = []

# vim:ts=4 sts=4 sw=4 et
