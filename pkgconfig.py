# encoding=UTF-8
# Copyright © 2008, 2009 Jakub Wilk <ubanus@users.sf.net>
#
# This package is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 dated June, 1991.
#
# This package is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

import subprocess

class IOError(IOError):
    pass

class Package(object):

    def __init__(self, name):
        self._name = name
    
    def variable(self, variable_name):
        pkgconfig = subprocess.Popen(
            ['pkg-config', '--variable=' + str(variable_name), self._name],
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE
        )
        stdout, stderr = pkgconfig.communicate()
        if pkgconfig.returncode:
            raise IOError(stderr.strip())
        return stdout.strip()

# vim:ts=4 sw=4 et
