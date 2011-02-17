# encoding=UTF-8
# Copyright © 2008, 2009 Jakub Wilk <jwilk@jwilk.net>
#
# This package is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 dated June, 1991.
#
# This package is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

SHARED_ANNOTATIONS_PAGENO = -1

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

__all__ = 'MultiPageModel', 'SHARED_ANNOTATIONS_PAGENO'

# vim:ts=4 sw=4 et
