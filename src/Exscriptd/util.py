# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import re
import imp

def resolve_variables(variables, string):
    def variable_sub_cb(match):
        field   = match.group(0)
        escape  = match.group(1)
        varname = match.group(2)
        value   = variables.get(varname)

        # Check the variable name syntax.
        if escape:
            return '$' + varname
        elif varname == '':
            return '$'

        # Check the variable value.
        if value is None:
            msg = 'Undefined variable %s' % repr(varname)
            raise Exception(msg)
        return str(value)

    string_re = re.compile(r'(\\?)\$([\w_]*)')
    return string_re.sub(variable_sub_cb, string)

def find_module_recursive(name, path = None):
    if not '.' in name:
        return imp.find_module(name, path)
    parent, children = name.split('.', 1)
    module = imp.find_module(parent, path)
    path   = module[1]
    return find_module_recursive(children, [path])

def synchronized(func):
    """
    Decorator for synchronizing method access.
    """
    def wrapped(self, *args, **kwargs):
        try:
            rlock = self._sync_lock
        except AttributeError:
            from threading import RLock
            rlock = self.__dict__.setdefault('_sync_lock', RLock())
        with rlock:
            return func(self, *args, **kwargs)

    wrapped.__name__ = func.__name__
    wrapped.__dict__ = func.__dict__
    wrapped.__doc__ = func.__doc__
    return wrapped
