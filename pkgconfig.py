# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>

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

# vim:ts=4 sw=4 noet
