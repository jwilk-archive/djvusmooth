#!/usr/bin/python
# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>

from cStringIO import StringIO

SHARED_ANNOTATIONS = -1

class Metadata(object):

	def __init__(self):
		self._pages = {}

	def __getitem__(self, n):
		if n not in self._pages:
			cls = PageMetadata
			if n == SHARED_ANNOTATIONS:
				cls = SharedMetadata
			metadata = self._pages[n] = cls(n, self.acquire_metadata(self, n))
		return metadata

	def acquire_metadata(self, n):
		return {}

	def export(self, djvused):
		for id in sorted(self._pages):
			self._pages[id].export(djvused)

class PageMetadata(dict):

	def __init__(self, n, original_data):
		self._old_data = None
		self._dirty = False
		self._n = n
		self.load(original_data, overwrite=True)

	def load(self, original_data, overwrite=False):
		if self._old_data is not None or overwrite:
			self._old_data = dict(original_data)
			self.revert()
	
	def export_select(self, djvused):
		djvused.select(self._n)

	def export(self, djvused):
		if not self._dirty:
			return
		self.export_select(self)
		djvused.set_meta(self)

	def revert(self, key = None):
		if key is None:
			self.clear()
			self.update(self._old_data)
			self._dirty = False
		else:
			try:
				self[key] = self._old_data[key]
			except KeyError:
				del self[key]

	def is_dirty(key = None):
		if key is None:
			return self._dirty
		new_value = self[key]
		try:
			return self._old_data[key] == new_value
		except KeyError:
			return True

class SharedMetadata(PageMetadata):
	
	def export_select(self, djvused):
		djvused.select_shared_annotations()

# vim:ts=4 sw=4
