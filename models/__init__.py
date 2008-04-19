# encoding=UTF-8
# Copyright © 2008 Jakub Wilk <ubanus@users.sf.net>

class MultiPageModel(object):

	def get_page_model_class(self, n):
		raise NotImplementedError

	def __init__(self):
		self._pages = {}

	def __getitem__(self, n):
		if n not in self._pages:
			cls = self.get_page_model_class(n)
			self._pages[n] = cls(n, self.acquire_data(n))
		return self._pages[n]
	
	def __setitem__(self, n, model):
		self._pages[n] = model

	def acquire_data(self, n):
		return {}

	def export(self, djvused):
		for id in sorted(self._pages):
			self._pages[id].export(djvused)

__all__ = 'MultiPageModel',

# vim:ts=4 sw=4
