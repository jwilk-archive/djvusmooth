# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>

import os.path
import subprocess

class Editor(object):

    def __call__(self, file_name):
        raise NotImplementedError

class RunMailcapEditor(object):

    def __call__(self, file_name):
        file_name = os.path.abspath(file_name)
        edit = subprocess.Popen(
            ['edit', 'text/plain:%s' % file_name],
            stdin = subprocess.PIPE,
            stdout = subprocess.PIPE,
        )
        edit.stdin.close()
        edit.stdout.close()
        edit.wait()

class CustomEditor(object):

    def __init__(self, command, *extra_args):
        self._command = [command]
        self._command += extra_args
    
    def __call__(self, file_name):
        file_name = os.path.abspath(file_name)
        edit = subprocess.Popen(
            self._command + [file_name],
            stdin = subprocess.PIPE,
            stdout = subprocess.PIPE,
        )
        edit.stdin.close()
        edit.stdout.close()
        edit.wait()

# vim:ts=4 sw=4 et
