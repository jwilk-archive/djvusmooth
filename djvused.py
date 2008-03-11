# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>

import pkgconfig
import os.path

DJVULIBRE_BIN_PATH = os.path.join(pkgconfig.Package('ddjvuapi').variable('exec_prefix'), 'bin')
DVJUSED_PATH = os.path.join(DJVULIBRE_BIN_PATH, 'djvused')

# vim:ts=4 sw=4 noet
