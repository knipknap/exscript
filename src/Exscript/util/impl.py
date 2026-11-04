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
Development tools.
"""

import sys
import traceback
import warnings
from collections.abc import Callable
from functools import wraps
from types import TracebackType
from typing import Any, Self


def add_label[T](obj: T, name: str, **kwargs: Any) -> T:
    """
    Labels an object such that it can later be checked with
    :class:`get_label()`.

    :type  obj: object
    :param obj: The object that is labeled.
    :type  name: str
    :param name: A label.
    :type  kwargs: dict
    :param kwargs: Optional values to store with the label.
    :rtype:  object
    :return: The labeled function.
    """
    labels = obj.__dict__.setdefault('_labels', dict())
    labels[name] = kwargs
    return obj


def get_label(obj: object, name: str) -> dict[str, Any] | None:
    """
    Checks whether an object has the given label attached (see
    :class:`add_label()`) and returns the associated options.

    :type  obj: object
    :param obj: The object to check for the label.
    :type  name: str
    :param name: A label.
    :rtype:  dict or None
    :return: The optional values if the label is attached, None otherwise.
    """
    labels: dict[str, dict[str, Any]] | None = obj.__dict__.get('_labels')
    if labels is None:
        return None
    return labels.get(name)


def copy_labels(src: object, dst: object) -> None:
    """
    Copies all labels of one object to another object.

    :type  src: object
    :param src: The object to check read the labels from.
    :type  dst: object
    :param dst: The object into which the labels are copied.
    """
    labels = src.__dict__.get('_labels')
    if labels is None:
        return
    dst.__dict__['_labels'] = labels.copy()


def serializeable_exc_info(
    thetype: type[BaseException] | None, ex: BaseException | None, tb: TracebackType | None
) -> tuple[type[BaseException] | None, BaseException | None, str]:
    """
    Returns the given exception info with the traceback formatted as a
    string, so that it can be pickled, unlike a traceback object.

    :return: The exception info, with the traceback formatted as a string.
    """
    return thetype, ex, ''.join(traceback.format_exception(thetype, ex, tb))


def serializeable_sys_exc_info() -> tuple[type[BaseException] | None, BaseException | None, str]:
    """
    Convenience wrapper around serializeable_exc_info, equivalent to
    serializeable_exc_info(sys.exc_info()).
    """
    return serializeable_exc_info(*sys.exc_info())


def format_exception(
    thetype: type[BaseException] | None, ex: BaseException | None, tb: TracebackType | str | None
) -> str:
    """
    Formats the given exception info like Python's
    traceback.format_exception(), but also accepts a traceback that is
    formatted as a string, as serializeable_exc_info() returns it.

    :return: The formatted exception; unlike Python's function, a string.
    """
    if isinstance(tb, str):
        return tb
    return ''.join(traceback.format_exception(thetype, ex, tb))


def deprecation(msg: str) -> None:
    """
    Issues a DeprecationWarning with the given message. Call it in the
    deprecated function: the warning points to the code that called that
    function.
    """
    warnings.warn(msg, category=DeprecationWarning, stacklevel=3)


def deprecated[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    """
    A decorator for marking functions as deprecated: each call of the
    function issues a DeprecationWarning that points to the calling code.
    """

    def decorated(*args: P.args, **kwargs: P.kwargs) -> R:
        deprecation('Call to deprecated function %s.' % func.__name__)
        return func(*args, **kwargs)

    decorated.__name__ = func.__name__
    decorated.__doc__ = func.__doc__
    decorated.__dict__.update(func.__dict__)
    return decorated


def synchronized[R](func: Callable[..., R]) -> Callable[..., R]:
    """
    Decorator for synchronizing method access.
    """

    @wraps(func)
    def wrapped(self: Any, *args: Any, **kwargs: Any) -> R:
        try:
            rlock = self._sync_lock
        except AttributeError:
            from multiprocessing import RLock

            rlock = self.__dict__.setdefault('_sync_lock', RLock())
        with rlock:
            return func(self, *args, **kwargs)

    return wrapped


def debug[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    """
    Decorator that prints a message whenever a function is entered or left.
    """

    @wraps(func)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        arg = repr(args) + ' ' + repr(kwargs)
        sys.stdout.write('Entering ' + func.__name__ + arg + '\n')
        try:
            result = func(*args, **kwargs)
        except:
            sys.stdout.write('Traceback caught:\n')
            sys.stdout.write(format_exception(*sys.exc_info()))
            raise
        arg = repr(result)
        sys.stdout.write('Leaving ' + func.__name__ + '(): ' + arg + '\n')
        return result

    return wrapped


class Decorator:
    """
    Wraps an object: the attributes of the wrapped object can be read and
    written through the wrapper, except for the attributes of the wrapper
    itself.
    """

    def __init__(self, obj: object) -> None:
        """
        Constructor.

        :param obj: The wrapped object.
        """
        self.__dict__['obj'] = obj

    def __setattr__(self, name: str, value: object) -> None:
        if name in list(self.__dict__.keys()):
            self.__dict__[name] = value
        else:
            setattr(self.obj, name, value)

    def __getattr__(self, name: str) -> Any:
        if name in list(self.__dict__.keys()):
            return self.__dict__[name]
        return getattr(self.obj, name)


class _Context(Decorator):
    """
    Wraps an object for a with statement that does nothing when it ends.
    """

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        thetype: type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        pass


class Context(_Context):
    """
    Wraps an object for a with statement that calls release() of the object
    when it ends, e.g. to release an account.
    """

    # Any: the result of release() of the wrapped object.
    def __exit__(
        self,
        thetype: type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> Any:
        return self.release()

    def context(self) -> _Context:
        """
        Returns a context for the wrapped object that does not call
        release() when it ends.
        """
        return _Context(self)
