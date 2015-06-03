# encoding=UTF-8

# Copyright © 2009-2012 Jakub Wilk <jwilk@jwilk.net>
#
# This package is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 dated June, 1991.
#
# This package is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

import errno
import os

class xdg(object):
    '''
    tiny replacement for PyXDG's xdg.BaseDirectory
    '''

    xdg_config_home = os.environ.get('XDG_CONFIG_HOME') or ''
    if os.name == 'nt' and xdg_config_home == '':
        # On Windows, use the “Application Data” folder if XDG_CONFIG_HOME is
        # not set.
        xdg_config_home = os.environ.get('APPDATA') or ''

    if not os.path.isabs(xdg_config_home):
        xdg_config_home = os.path.join(os.path.expanduser('~'), '.config')

    xdg_config_dirs = os.environ.get('XDG_CONFIG_DIRS') or '/etc/xdg'
    xdg_config_dirs = (
        [xdg_config_home] +
        filter(os.path.abspath, xdg_config_dirs.split(os.path.pathsep))
    )

    @classmethod
    def save_config_path(xdg, resource):
        path = os.path.join(xdg.xdg_config_home, resource)
        try:
            os.makedirs(path, 0700)
        except OSError:
            if not os.path.isdir(path):
                raise
        return path

    @classmethod
    def load_config_paths(xdg, resource):
        for config_dir in xdg.xdg_config_dirs:
            path = os.path.join(config_dir, resource)
            if os.path.exists(path):
                yield path

class Config(object):

    def __init__(self, resource, legacy_path=None):
        self._dirty = False
        self._data = {}
        self._resource = resource
        for directory in xdg.load_config_paths(resource):
            self._load(os.path.join(directory, '%s.conf' % resource))
        self._legacy_path = legacy_path
        if legacy_path is not None:
            self._load(legacy_path)
            self._dirty = True

    def read(self, key, default):
        return self._data.get(key, default)

    def read_int(self, key, default):
        return int(self.read(key, default))

    def read_bool(self, key, default):
        return bool(self.read_int(key, default))

    def __setitem__(self, key, value):
        self._data[key] = value
        self._dirty = True

    def del_array(self, key):
        keys_to_delete = frozenset(
            k for k in self._data
            if k.startswith(key + '[')
        )
        for k in keys_to_delete:
            del self._data[k]

    def _load(self, path):
        try:
            file = open(path, 'r')
        except IOError as ex:
            if ex.errno == errno.ENOENT:
                return
        try:
            for line in file:
                line = line.rstrip()
                try:
                    key, value = line.split('=', 1)
                except ValueError:
                    pass
                value = value.decode('UTF-8')
                self._data[key] = value
        finally:
            file.close()

    def flush(self):
        if not self._dirty:
            return
        directory = xdg.save_config_path(self._resource)
        path = os.path.join(directory, '%s.conf' % self._resource)
        tmp_path = path + '.tmp'
        file = open(tmp_path, 'w')
        try:
            for key, value in sorted(self._data.iteritems()):
                if isinstance(value, unicode):
                    value = value.encode('UTF-8')
                file.write('%s=%s\n' % (key, value))
            file.flush()
            os.fsync(file.fileno())
        finally:
            file.close()
        if os.name != 'posix' and os.path.exists(path):
            # Atomic renames might be not supported.
            backup_path = path + '.bak'
            os.rename(path, backup_path)
            os.rename(tmp_path, path)
            os.remove(backup_path)
        else:
            os.rename(tmp_path, path)
        if self._legacy_path is not None:
            try:
                os.remove(self._legacy_path)
            except OSError as ex:
                if ex.errno != errno.ENOENT:
                    raise
        self._dirty = False

# vim:ts=4 sts=4 sw=4 et
