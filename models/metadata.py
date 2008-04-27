#!/usr/bin/python
# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>


'''
Models for metadata.

See ``djvuchanges.txt``:
- 4. Metadata Annotations. 
- 5. Document Annotations and Metadata.
'''

from cStringIO import StringIO
from models import MultiPageModel, SHARED_ANNOTATIONS_PAGENO

class Metadata(MultiPageModel):

	def get_page_model_class(self, n):
		cls = PageMetadata
		if n == SHARED_ANNOTATIONS_PAGENO:
			return SharedMetadata
		else:
			return PageMetadata
			
class PageMetadata(dict):

	def __init__(self, n, original_data):
		self._old_data = None
		self._dirty = False
		self._n = n
		self.load(original_data, overwrite=True)

	def __setitem__(self, key, value):
		self._dirty = True
		dict.__setitem__(self, key, value)

	def clone(self):
		from copy import copy
		return copy(self)

	def load(self, original_data, overwrite=False):
		if self._old_data is not None or overwrite:
			self._old_data = dict(original_data)
			self.revert()
	
	def export_select(self, djvused):
		djvused.select(self._n + 1)

	def export(self, djvused):
		if not self._dirty:
			return
		self.export_select(djvused)
		djvused.set_metadata(self)

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
		djvused.create_shared_annotations()

__all__ = 'Metadata', 'PageMetadata', 'SharedMetadata'

# vim:ts=4 sw=4
