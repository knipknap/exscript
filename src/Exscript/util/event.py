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
A simple signal/event mechanism.
"""
from threading     import Lock
from Exscript.util import weakmethod

class Event(object):
    """
    A simple signal/event mechanism, to be used like this::

        def mycallback(arg, **kwargs):
            print arg, kwargs['foo']

        myevent = Event()
        myevent.connect(mycallback)
        myevent.emit('test', foo = 'bar')
        # Or just: myevent('test', foo = 'bar')
    """

    def __init__(self):
        """
        Constructor.
        """
        self.lock             = Lock()
        self.weak_subscribers = []
        self.hard_subscribers = []

    def __call__(self, *args, **kwargs):
        """
        Like emit().
        """
        return self.emit(*args, **kwargs)

    def connect(self, callback, *args, **kwargs):
        """
        Connects the event with the given callback.
        When the signal is emitted, the callback is invoked.

        @note: The signal handler is stored with a hard reference, so you
        need to make sure to call L{disconnect()} if you want the handler
        to be garbage collected.

        @type  callback: object
        @param callback: The callback function.
        @type  args: tuple
        @param args: Optional arguments passed to the callback.
        @type  kwargs: dict
        @param kwargs: Optional keyword arguments passed to the callback.
        """
        if self.is_connected(callback):
            raise AttributeError('callback is already connected')
        self.hard_subscribers.append((callback, args, kwargs))

    def listen(self, callback, *args, **kwargs):
        """
        Like L{connect()}, but uses a weak reference instead of a
        normal reference.
        The signal is automatically disconnected as soon as the handler
        is garbage collected.

        @note: Storing signal handlers as weak references means that if
        your handler is a local function, it may be garbage collected. To
        prevent this, use L{connect()} instead.

        @type  callback: object
        @param callback: The callback function.
        @type  args: tuple
        @param args: Optional arguments passed to the callback.
        @type  kwargs: dict
        @param kwargs: Optional keyword arguments passed to the callback.
        @rtype:  L{Exscript.util.weakmethod.WeakMethod}
        @return: The newly created weak reference to the callback.
        """
        with self.lock:
            if self.is_connected(callback):
                raise AttributeError('callback is already connected')
            ref = weakmethod.ref(callback, self._try_disconnect)
            self.weak_subscribers.append((ref, args, kwargs))
        return ref

    def n_subscribers(self):
        """
        Returns the number of connected subscribers.

        @rtype:  int
        @return: The number of subscribers.
        """
        return len(self.hard_subscribers) + len(self.weak_subscribers)

    def _hard_callbacks(self):
        return [s[0] for s in self.hard_subscribers]

    def _weakly_connected_index(self, callback):
        weak = [s[0].get_function() for s in self.weak_subscribers]
        try:
            return weak.index(callback)
        except ValueError:
            return None

    def is_connected(self, callback):
        """
        Returns True if the event is connected to the given function.

        @type  callback: object
        @param callback: The callback function.
        @rtype:  bool
        @return: Whether the signal is connected to the given function.
        """
        index = self._weakly_connected_index(callback)
        if index is not None:
            return True
        return callback in self._hard_callbacks()

    def emit(self, *args, **kwargs):
        """
        Emits the signal, passing the given arguments to the callbacks.

        @type  args: tuple
        @param args: Optional arguments passed to the callbacks.
        @type  kwargs: dict
        @param kwargs: Optional keyword arguments passed to the callbacks.
        """
        for callback, user_args, user_kwargs in self.hard_subscribers:
            kwargs.update(user_kwargs)
            callback(*args + user_args, **kwargs)

        for callback, user_args, user_kwargs in self.weak_subscribers:
            kwargs.update(user_kwargs)

            # Even though WeakMethod notifies us when the underlying
            # function is destroyed, and we remove the item from the
            # the list of subscribers, there is no guarantee that
            # this notification has already happened because the garbage
            # collector may run while this loop is executed.
            # Disabling the garbage collector temporarily also does
            # not work, because other threads may be trying to do
            # the same, causing yet another race condition.
            # So the only solution is to skip such functions.
            function = callback.get_function()
            if function is None:
                continue
            function(*args + user_args, **kwargs)

    def _try_disconnect(self, ref):
        with self.lock:
            weak = [s[0] for s in self.weak_subscribers]
            try:
                index = weak.index(ref)
            except ValueError:
                # subscriber was already removed by a call to disconnect()
                pass
            else:
                self.weak_subscribers.pop(index)

    def disconnect(self, callback):
        """
        Disconnects the signal from the given function.

        @type  callback: object
        @param callback: The callback function.
        """
        with self.lock:
            index = self._weakly_connected_index(callback)
            if index is not None:
                self.weak_subscribers.pop(index)[0]
        try:
            index = self._hard_callbacks().index(callback)
        except ValueError:
            pass
        else:
            self.hard_subscribers.pop(index)

    def disconnect_all(self):
        """
        Disconnects all connected functions from all signals.
        """
        self.hard_subscribers = []
        self.weak_subscribers = []
