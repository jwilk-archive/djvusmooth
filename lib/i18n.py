# encoding=UTF-8

# Copyright © 2009 Jakub Wilk <jwilk@jwilk.net>
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

import gettext
import os
import sys

for dir in os.path.join(os.path.dirname(sys.argv[0]), 'locale'), None:
    try:
        _ = gettext.translation('djvusmooth', dir).ugettext
        break
    except IOError:
        pass
else:
    def _(s):
        return s
del dir

# Some dummy translations:
if False:
    _('page')
    _('column')
    _('region')
    _('para')
    _('line')
    _('word')
    _('char')
    _('bookmarks')

# vim:ts=4 sts=4 sw=4 et
