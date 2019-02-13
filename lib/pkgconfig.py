# encoding=UTF-8

# Copyright © 2008-2019 Jakub Wilk <jwilk@jwilk.net>
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

from . import ipc

class IOError(IOError):
    pass

class Package(object):

    def __init__(self, name):
        self._name = name

    def variable(self, variable_name):
        pkgconfig = ipc.Subprocess(
            ['pkg-config', '--variable=' + str(variable_name), self._name],
            stdout=ipc.PIPE,
            stderr=ipc.PIPE
        )
        stdout, stderr = pkgconfig.communicate()
        if pkgconfig.returncode:
            raise IOError(stderr.strip())
        return stdout.strip()

# vim:ts=4 sts=4 sw=4 et
