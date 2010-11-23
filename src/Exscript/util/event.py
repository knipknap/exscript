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
A simple signal/even mechanism.
"""

class Event(object):
    """
    A simple signal/even mechanism, to be used like this::

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
        self.subscribers = []

    def __call__(self, *args, **kwargs):
        """
        Like emit().
        """
        return self.emit(*args, **kwargs)

    def connect(self, callback, *args, **kwargs):
        """
        Connects the event with the given callback.
        When the signal is emitted, the callback is invoked.

        @type  callback: object
        @param callback: The callback function.
        @type  args: tuple
        @param args: Optional arguments passed to the callback.
        @type  kwargs: dict
        @param kwargs: Optional keyword arguments passed to the callback.
        """
        if callback in [s[0] for s in self.subscribers]:
            raise AttributeError('callback is already connected')
        self.subscribers.append((callback, args, kwargs))

    def n_subscribers(self):
        """
        Returns the number of connected subscribers.

        @rtype:  int
        @return: The number of subscribers.
        """
        return len(self.subscribers)

    def is_connected(self, callback):
        """
        Returns True if the event is connected to the given function.

        @type  callback: object
        @param callback: The callback function.
        @rtype:  bool
        @return: Whether the signal is connected to the given function.
        """
        return callback in [s[0] for s in self.subscribers]

    def emit(self, *args, **kwargs):
        """
        Emits the signal, passing the given arguments to the callbacks.

        @type  args: tuple
        @param args: Optional arguments passed to the callbacks.
        @type  kwargs: dict
        @param kwargs: Optional keyword arguments passed to the callbacks.
        """
        for callback, user_args, user_kwargs in self.subscribers:
            kwargs.update(user_kwargs)
            callback(*args + user_args, **kwargs)

    def disconnect(self, callback):
        """
        Disconnects the signal from the given function.

        @type  callback: object
        @param callback: The callback function.
        """
        item = [s[0] for s in self.subscribers].index(callback)
        self.subscribers.pop(item)

    def disconnect_all(self):
        """
        Disconnects all connected functions from all signals.
        """
        self.subscribers = []
