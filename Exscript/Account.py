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
Representing user accounts.
"""
from __future__ import unicode_literals
from builtins import object
import multiprocessing
from Exscript.util.event import Event
from Exscript.util.impl import Context


class Account(object):

    """
    This class represents a user account.
    """

    def __init__(self,
                 name,
                 password='',
                 password2=None,
                 key=None,
                 needs_lock=True):
        """
        Constructor.

        The authorization password is only required on hosts that
        separate the authentication from the authorization procedure.
        If an authorization password is not given, it defaults to the
        same value as the authentication password.

        If the `needs_lock` argument is set to True, we ensure that no
        two threads can use the same account at the same time. You will
        want to use this setting if you are using a central authentication
        server that allows for only one login to happen at a time.
        Note that you will still be able to open multiple sessions at the
        time. It is only the authentication procedure that will not happen
        in parallel; once the login is complete, other threads can use
        the account again.
        In other words, the account is only locked during calls to
        :meth:`protocols.Protocol.login` and the `*authenticate*` methods.

        .. warning::
            Setting `lock` to True drastically degrades performance!

        :type  name: str
        :param name: A username.
        :type  password: str
        :param password: The authentication password.
        :type  password2: str
        :param password2: The authorization password, if required.
        :type  key: PrivateKey
        :param key: A private key, if required.
        :type needs_lock: bool
        :param needs_lock: True if the account will be locked during login.
        """
        self.acquired_event = Event()
        self.released_event = Event()
        self.changed_event = Event()
        self.name = name
        self.password = password
        self.authorization_password = password2
        self.key = key
        self.synclock = multiprocessing.Condition(multiprocessing.Lock())
        self.lock = multiprocessing.Lock()
        self.needs_lock = needs_lock

    def __enter__(self):
        if self.needs_lock:
            self.acquire()
        return self

    def __exit__(self, thetype, value, traceback):
        if self.needs_lock:
            self.release()

    def context(self):
        """
        When you need a 'with' context for an already-acquired account.
        """
        return Context(self)

    def acquire(self, signal=True):
        """
        Locks the account.
        Method has no effect if the constructor argument `needs_lock`
        wsa set to False.

        :type signal: bool
        :param signal: Whether to emit the acquired_event signal.
        """
        if not self.needs_lock:
            return
        with self.synclock:
            while not self.lock.acquire(False):
                self.synclock.wait()
            if signal:
                self.acquired_event(self)
            self.synclock.notify_all()

    def release(self, signal=True):
        """
        Unlocks the account.
        Method has no effect if the constructor argument `needs_lock`
        wsa set to False.

        :type signal: bool
        :param signal: Whether to emit the released_event signal.
        """
        if not self.needs_lock:
            return
        with self.synclock:
            self.lock.release()
            if signal:
                self.released_event(self)
            self.synclock.notify_all()

    def set_name(self, name):
        """
        Changes the name of the account.

        :type  name: string
        :param name: The account name.
        """
        self.name = name
        self.changed_event.emit(self)

    def get_name(self):
        """
        Returns the name of the account.

        :rtype:  string
        :return: The account name.
        """
        return self.name

    def set_password(self, password):
        """
        Changes the password of the account.

        :type  password: string
        :param password: The account password.
        """
        self.password = password
        self.changed_event.emit(self)

    def get_password(self):
        """
        Returns the password of the account.

        :rtype:  string
        :return: The account password.
        """
        return self.password

    def set_authorization_password(self, password):
        """
        Changes the authorization password of the account.

        :type  password: string
        :param password: The new authorization password.
        """
        self.authorization_password = password
        self.changed_event.emit(self)

    def get_authorization_password(self):
        """
        Returns the authorization password of the account.

        :rtype:  string
        :return: The account password.
        """
        return self.authorization_password or self.password

    def get_key(self):
        """
        Returns the key of the account, if any.

        :rtype:  PrivateKey|None
        :return: A key object.
        """
        return self.key
