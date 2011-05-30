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
"""
Development tools.
"""
import sys
import warnings
import traceback
from functools import wraps

def serializeable_exc_info(thetype, ex, tb):
    """
    Since traceback objects can not be pickled, this function manipulates
    exception info tuples before they are passed accross process
    boundaries.
    """
    return thetype, ex, ''.join(traceback.format_exception(thetype, ex, tb))

def serializeable_sys_exc_info():
    """
    Convenience wrapper around serializeable_exc_info, equivalent to
    serializeable_exc_info(sys.exc_info()).
    """
    return serializeable_exc_info(*sys.exc_info())

def format_exception(thetype, ex, tb):
    """
    This function is a drop-in replacement for Python's
    traceback.format_exception().

    Since traceback objects can not be pickled, Exscript is forced to
    manipulate them before they are passed accross process boundaries.
    This leads to the fact the Python's traceback.format_exception()
    no longer works for those objects.

    This function works with any traceback object, regardless of whether
    or not Exscript manipulated it.
    """
    if isinstance(tb, str):
        return tb
    return ''.join(traceback.format_exception(thetype, ex, tb))

def deprecation(msg):
    """
    Prints a deprecation warning.
    """
    warnings.warn('deprecated',
                  category   = DeprecationWarning,
                  stacklevel = 2)

def deprecated(func):
    """
    A decorator for marking functions as deprecated. Results in
    a printed warning message when the function is used.
    """
    def decorated(*args, **kwargs):
        warnings.warn('Call to deprecated function %s.' % func.__name__,
                      category   = DeprecationWarning,
                      stacklevel = 2)
        return func(*args, **kwargs)
    decorated.__name__ = func.__name__
    decorated.__doc__  = func.__doc__
    decorated.__dict__.update(func.__dict__)
    return decorated

def synchronized(func):
    """
    Decorator for synchronizing method access.
    """
    @wraps(func)
    def wrapped(self, *args, **kwargs):
        try:
            rlock = self._sync_lock
        except AttributeError:
            from multiprocessing import RLock
            rlock = self.__dict__.setdefault('_sync_lock', RLock())
        with rlock:
            return func(self, *args, **kwargs)
    return wrapped
