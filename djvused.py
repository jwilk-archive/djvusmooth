# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>

import pkgconfig
import os.path
import subprocess
import threading

from djvu.sexpr import Expression, Symbol

try:
    DJVULIBRE_BIN_PATH = os.path.join(pkgconfig.Package('ddjvuapi').variable('exec_prefix'), 'bin')
except IOError:
    DJVULIBRE_BIN_PATH = None
    DJVUSED_PATH = 'djvused'
else:
    DJVUSED_PATH = os.path.join(DJVULIBRE_BIN_PATH, 'djvused')

def _djvused_usability_check():
    djvused = subprocess.Popen([DJVUSED_PATH], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    djvused.communicate()
    if djvused.returncode != 10:
        raise IOError('%r does not seem to be usable' % DJVUSED_PATH)

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
        args = [DJVUSED_PATH]
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

# vim:ts=4 sw=4 et
