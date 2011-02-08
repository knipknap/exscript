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
Weak references to bound and unbound methods.
"""
import weakref

class WeakMethod(object):
    def __init__(self, callback):
        self.callback = callback

    def _dead(self, ref):
        if self.callback is not None:
            self.callback(self)

    def get_function(self):
        return None

    def isalive(self):
        return self.get_function() is not None

class WeakMethodBound(WeakMethod):
    def __init__(self, f, callback):
        WeakMethod.__init__(self, callback)
        self.f = f
        self.c = weakref.ref(f.__self__, self._dead)

    def get_function(self):
        if self.c() is None:
            return None
        return self.f

    def __call__(self, *args, **kwargs):
        if not self.isalive():
            raise TypeError, 'Method called on dead object'
        return self.f(*args, **kwargs)

class WeakMethodFree(WeakMethod):
    def __init__(self, f, callback):
        WeakMethod.__init__(self, callback)
        self.f = weakref.ref(f, self._dead)

    def get_function(self):
        return self.f()

    def __call__(self, *args, **kwargs):
        method = self.f()
        if method is None:
            raise TypeError, 'Function no longer exist'
        method(*args, **kwargs)

def ref(f, callback):
    try:
        f.__func__
    except AttributeError:
        return WeakMethodFree(f, callback)
    return WeakMethodBound(f, callback)
