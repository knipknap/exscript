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
A simple signal/event mechanism.
"""

from collections.abc import Callable
from threading import Lock
from typing import Any, cast

from . import weakmethod


class Event:
    """
    A simple signal/event mechanism, to be used like this::

        def mycallback(arg, **kwargs):
            print(arg, kwargs['foo'])

        myevent = Event()
        myevent.connect(mycallback)
        myevent.emit('test', foo = 'bar')
        # Or just: myevent('test', foo = 'bar')
    """

    def __init__(self) -> None:
        """
        Constructor.
        """
        # To save memory, the lock and the subscriber lists are created only
        # when needed: events are used so widely in Exscript that this makes
        # a big difference to the memory footprint.
        self.lock: Lock | None = None
        self.weak_subscribers: (
            list[tuple[weakmethod.WeakMethod, tuple[Any, ...], dict[str, Any]]] | None
        ) = None
        self.hard_subscribers: (
            list[tuple[Callable[..., Any], tuple[Any, ...], dict[str, Any]]] | None
        ) = None

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """
        Like emit().
        """
        return self.emit(*args, **kwargs)

    def connect(self, callback: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        """
        Connects the event with the given callback.
        When the signal is emitted, the callback is invoked.

        .. HINT::
            The signal handler is stored with a hard reference, so you
            need to make sure to call :class:`disconnect()` if you want the handler
            to be garbage collected.

        :type  callback: callable
        :param callback: The callback function.
        :type  args: tuple
        :param args: Optional arguments passed to the callback.
        :type  kwargs: dict
        :param kwargs: Optional keyword arguments passed to the callback.
        """
        if self.is_connected(callback):
            raise AttributeError('callback is already connected')
        if self.hard_subscribers is None:
            self.hard_subscribers = []
        self.hard_subscribers.append((callback, args, kwargs))

    def listen(
        self, callback: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> weakmethod.WeakMethod:
        """
        Like :class:`connect()`, but uses a weak reference instead of a
        normal reference.
        The signal is automatically disconnected as soon as the handler
        is garbage collected.

        .. HINT::
            Storing signal handlers as weak references means that if
            your handler is a local function, it may be garbage collected. To
            prevent this, use :class:`connect()` instead.

        :type  callback: callable
        :param callback: The callback function.
        :type  args: tuple
        :param args: Optional arguments passed to the callback.
        :type  kwargs: dict
        :param kwargs: Optional keyword arguments passed to the callback.
        :rtype:  :class:`Exscript.util.weakmethod.WeakMethod`
        :return: The newly created weak reference to the callback.
        """
        if self.lock is None:
            self.lock = Lock()
        with self.lock:
            if self.is_connected(callback):
                raise AttributeError('callback is already connected')
            if self.weak_subscribers is None:
                self.weak_subscribers = []
            ref = weakmethod.ref(callback, self._try_disconnect)
            self.weak_subscribers.append((ref, args, kwargs))
        return ref

    def n_subscribers(self) -> int:
        """
        Returns the number of connected subscribers.

        :rtype:  int
        :return: The number of subscribers.
        """
        hard = self.hard_subscribers and len(self.hard_subscribers) or 0
        weak = self.weak_subscribers and len(self.weak_subscribers) or 0
        return hard + weak

    def _hard_callbacks(self) -> list[Callable[..., Any]]:
        """
        Returns the callbacks that are connected with a hard reference.
        Only called if there are hard subscribers.
        """
        return [s[0] for s in cast('list[Any]', self.hard_subscribers)]

    def _weakly_connected_index(self, callback: Callable[..., Any]) -> int | None:
        """
        Returns the index of the given callback in the list of weak
        subscribers, or None if it is not connected with a weak reference.
        """
        if self.weak_subscribers is None:
            return None
        weak = [s[0].get_function() for s in self.weak_subscribers]
        try:
            return weak.index(callback)
        except ValueError:
            return None

    def is_connected(self, callback: Callable[..., Any]) -> bool:
        """
        Returns True if the event is connected to the given function.

        :type  callback: callable
        :param callback: The callback function.
        :rtype:  bool
        :return: Whether the signal is connected to the given function.
        """
        index = self._weakly_connected_index(callback)
        if index is not None:
            return True
        if self.hard_subscribers is None:
            return False
        return callback in self._hard_callbacks()

    def emit(self, *args: Any, **kwargs: Any) -> Any:
        """
        Emits the signal, passing the given arguments to the callbacks.
        If one of the callbacks returns a value other than None, no further
        callbacks are invoked and the return value of the callback is
        returned to the caller of emit().

        :type  args: tuple
        :param args: Optional arguments passed to the callbacks.
        :type  kwargs: dict
        :param kwargs: Optional keyword arguments passed to the callbacks.
        :rtype:  object
        :return: Returns None if all callbacks returned None. Returns
                 the return value of the last invoked callback otherwise.
        """
        if self.hard_subscribers is not None:
            for callback, user_args, user_kwargs in self.hard_subscribers:
                kwargs.update(user_kwargs)
                result = callback(*args + user_args, **kwargs)
                if result is not None:
                    return result

        if self.weak_subscribers is not None:
            for callback, user_args, user_kwargs in self.weak_subscribers:
                kwargs.update(user_kwargs)

                # The garbage collector may destroy the function during this
                # loop, before WeakMethod's notification removes it; disabling
                # the collector would race with other threads. So skip it.
                function = callback.get_function()
                if function is None:
                    continue
                result = function(*args + user_args, **kwargs)
                if result is not None:
                    return result

    def _try_disconnect(self, ref: weakmethod.WeakMethod) -> None:
        """
        Called by the weak reference when its target dies.
        In other words, we can assert that self.weak_subscribers is not
        None at this time.
        """
        with cast(Lock, self.lock):
            weak = [s[0] for s in cast('list[Any]', self.weak_subscribers)]
            try:
                index = weak.index(ref)
            except ValueError:
                # subscriber was already removed by a call to disconnect()
                pass
            else:
                cast('list[Any]', self.weak_subscribers).pop(index)

    def disconnect(self, callback: Callable[..., Any]) -> None:
        """
        Disconnects the signal from the given function.

        :type  callback: callable
        :param callback: The callback function.
        """
        if self.weak_subscribers is not None:
            with cast(Lock, self.lock):  # listen() creates the lock first
                index = self._weakly_connected_index(callback)
                if index is not None:
                    self.weak_subscribers.pop(index)[0]
        if self.hard_subscribers is not None:
            try:
                index = self._hard_callbacks().index(callback)
            except ValueError:
                pass
            else:
                self.hard_subscribers.pop(index)

    def disconnect_all(self) -> None:
        """
        Disconnects all connected functions from all signals.
        """
        self.hard_subscribers = None
        self.weak_subscribers = None
