# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>

import os.path
import subprocess

def edit(file_name):
	# FIXME: use something less Debian-specific
	file_name = os.path.abspath(file_name)
	edit = subprocess.Popen(
		['edit', 'text/plain:%s' % file_name],
		stdin = subprocess.PIPE,
		stdout = subprocess.PIPE
	)
	edit.stdin.close()
	edit.stdout.close()
	edit.wait()

# vim:ts=4 sw=4
