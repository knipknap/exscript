#
# Copyright (C) 2010-2017 Samuel Abels
# The MIT License (MIT)
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Weak references to bound and unbound methods.
"""

import weakref
from collections.abc import Callable
from types import MethodType
from typing import Any, cast


class DeadMethodCalled(Exception):
    """
    Raised by :class:`WeakMethod` if it is called when the referenced object
    is already dead.
    """

    pass


class WeakMethod:
    """
    Do not create this class directly; use :class:`ref()` instead.
    """

    __slots__ = 'name', 'callback'

    def __init__(self, name: str, callback: 'Callable[[WeakMethod], object] | None') -> None:
        """
        Constructor. Do not use directly, use :class:`ref()` instead.
        """
        self.name = name
        self.callback = callback

    def _dead(self, ref: weakref.ref[Any]) -> None:
        """
        Called when the referenced object dies; passes this weak reference
        to the callback, if any.
        """
        if self.callback is not None:
            self.callback(self)

    def get_function(self) -> Callable[..., Any] | None:
        """
        Returns the referenced method/function if it is still alive.
        Returns None otherwise.

        :rtype:  callable|None
        :return: The referenced function if it is still alive.
        """
        raise NotImplementedError()

    def isalive(self) -> bool:
        """
        Returns True if the referenced function is still alive, False
        otherwise.

        :rtype:  bool
        :return: Whether the referenced function is still alive.
        """
        return self.get_function() is not None

    def __call__(self, *args: Any, **kwargs: Any) -> None:
        """
        Proxied to the underlying function or method. Raises :class:`DeadMethodCalled`
        if the referenced function is dead. The result of the function is
        discarded.
        """
        method = self.get_function()
        if method is None:
            raise DeadMethodCalled('method called on dead object ' + self.name)
        method(*args, **kwargs)


class _WeakMethodBound(WeakMethod):
    """
    A weak reference to a bound method. Only the object of the method is
    referenced weakly; the method is looked up by its name when needed.
    """

    __slots__ = 'name', 'callback', 'f', 'c'

    def __init__(self, f: MethodType, callback: Callable[[WeakMethod], object] | None) -> None:
        """
        Constructor.

        :param f: The bound method.
        :param callback: Called with this object when the object of the
            method dies.
        """
        name = f.__self__.__class__.__name__ + '.' + f.__func__.__name__
        WeakMethod.__init__(self, name, callback)
        self.f = f.__func__
        self.c = weakref.ref(f.__self__, self._dead)

    def get_function(self) -> Callable[..., Any] | None:
        """
        Returns the method, bound to the object if it is still alive.
        Returns None otherwise.
        """
        cls = self.c()
        if cls is None:
            return None
        return cast('Callable[..., Any]', getattr(cls, self.f.__name__))


class _WeakMethodFree(WeakMethod):
    """
    A weak reference to a function or another callable object that is not
    a bound method.
    """

    __slots__ = 'name', 'callback', 'f'

    def __init__(
        self, f: Callable[..., Any], callback: Callable[[WeakMethod], object] | None
    ) -> None:
        """
        Constructor.

        :param f: The function.
        :param callback: Called with this object when the function dies.
        """
        WeakMethod.__init__(self, f.__class__.__name__, callback)
        self.f = weakref.ref(f, self._dead)

    def get_function(self) -> Callable[..., Any] | None:
        """
        Returns the function if it is still alive, None otherwise.
        """
        return self.f()


def ref(
    function: Callable[..., Any], callback: Callable[[WeakMethod], object] | None = None
) -> WeakMethod:
    """
    Returns a weak reference to the given method or function.
    If the callback argument is not None, it is called as soon
    as the referenced function is garbage deleted.

    :type  function: callable
    :param function: The function to reference.
    :type  callback: callable
    :param callback: Called when the function dies.
    """
    # A bound method is recognized by its __func__ attribute.
    try:
        cast(MethodType, function).__func__
    except AttributeError:
        return _WeakMethodFree(function, callback)
    return _WeakMethodBound(cast(MethodType, function), callback)
