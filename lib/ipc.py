# encoding=UTF-8

# Copyright © 2010-2019 Jakub Wilk <jwilk@jwilk.net>
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

'''interprocess communication'''

import os
import signal

if os.name == 'posix':
    import subprocess32 as subprocess
else:
    import subprocess

Subprocess = subprocess.Popen
PIPE = subprocess.PIPE

# Protect from scanadf and possibly other software that sets SIGCHLD to
# SIG_IGN.
# https://bugs.debian.org/596232
if os.name == 'posix':
    signal.signal(signal.SIGCHLD, signal.SIG_DFL)

__all__ = ['Subprocess', 'PIPE']

# vim:ts=4 sts=4 sw=4 et
