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
Accessing the connection to a remote host.
"""
import threading
import os
from Account import Account

class Connection(object):
    """
    This class is a decorator for protocols.Transport objects that
    adds thread safety by adding locking to the authenticate() and
    authorize() functions.
    It also provides access to the associated Queue and Host instances.

    For complete documentation, please refer to the protocols.Transport
    documentation.
    """

    def __init__(self, action, **kwargs):
        """
        Do not call directly; Exscript creates the connection for you and
        passes it to the function that is invoked by Queue.run().

        @type  action: HostAction
        @param action: The associated HostAction instance.
        @type  kwargs: dict
        @param kwargs: Same as L{protocols.Transport}.
        """
        # Since we override setattr below, we can't access our properties
        # directly.
        self.__dict__['action'] = action

        # If specified, use the host-specific login details.
        host = action.get_host()
        self.__dict__['default_account'] = None
        if host.get_username() is not None:
            account = Account(host.get_username(),
                              host.get_password(),
                              host.get_password2())
            self.__dict__['default_account'] = account

        # Define protocol specific options.
        queue = action.get_queue()
        if host.get_tcp_port() is not None:
            kwargs['port'] = host.get_tcp_port()

        # Create an instance of the protocol adapter.
        kwargs['stdout'] = queue._get_channel('connection')
        protocol_name    = host.get_protocol()
        protocol         = queue._get_protocol_from_name(protocol_name)
        transport        = protocol(**kwargs)
        self.__dict__['transport'] = transport

        # Define the behaviour of the pseudo protocol adapter.
        if protocol_name == 'pseudo':
            filename = host.get_address()
            hostname = os.path.basename(filename)
            transport.device.add_commands_from_file(filename)


    def __copy__(self):
        """
        Overwritten to return the very same object instead of copying the
        stream, because copying a network connection is impossible.

        @rtype:  Transport
        @return: self
        """
        return self


    def __deepcopy__(self, memo):
        """
        Overwritten to return the very same object instead of copying the
        stream, because copying a network connection is impossible.

        @type  memo: object
        @param memo: Please refer to Python's standard library documentation.
        @rtype:  Transport
        @return: self
        """
        return self


    def __setattr__(self, name, value):
        """
        Overwritten to proxy any calls to the associated protocol adapter
        (decorator pattern).

        @type  name: string
        @param name: The attribute name.
        @type  value: string
        @param value: The attribute value.
        """
        if name in self.__dict__.keys():
            self.__dict__[name] = value
        else:
            setattr(self.transport, name, value)

    def __getattr__(self, name):
        """
        Overwritten to proxy any calls to the associated protocol adapter
        (decorator pattern).

        @type  name: string
        @param name: The attribute name.
        @rtype:  object
        @return: Whatever the transport adapter returns.
        """
        if name in self.__dict__.keys():
            return self.__dict__[name]
        return getattr(self.transport, name)

    def _on_otp_requested(self, key, seq, account):
        account.otp_requested_event(account, key, seq)

    def _track_account(self, account):
        cb = self._on_otp_requested
        self.transport.otp_requested_event.connect(cb, account)

    def _untrack_accounts(self):
        cb = self._on_otp_requested
        self.transport.otp_requested_event.disconnect(cb)

    def _acquire_account(self, account = None, lock = True):
        # Specific account requested?
        if account:
            if lock:
                account.acquire()
            return account

        # Is a default account defined for this connection?
        if self.default_account:
            if lock:
                self.default_account.acquire()
            return self.default_account

        # Else, choose an account from the account pool.
        if lock:
            return self.get_account_manager().acquire_account()
        raise Exception('non-locking shared accounts are not supported.')

    def _release_account(self, account):
        account.release()

    def get_action(self):
        """
        Returns the associated HostAction instance.

        @rtype:  HostAction
        @return: The associated HostAction instance.
        """
        return self.action

    def get_queue(self):
        """
        Returns the associated Queue instance.

        @rtype:  Queue
        @return: The associated Queue instance.
        """
        return self.action.get_queue()

    def get_account_manager(self):
        """
        Returns the associated account manager.

        @rtype:  AccountManager
        @return: The associated account manager.
        """
        return self.get_queue().account_manager

    def get_host(self):
        """
        Returns the host on which the job is performed.

        @rtype:  Host
        @return: The Host instance.
        """
        return self.action.get_host()

    def open(self):
        """
        Opens the connection to the remote host.
        """
        if not self.transport.connect(self.get_host().get_address(),
                                      self.get_host().get_tcp_port()):
            raise Exception('Connection failed.')

    def login(self, account = None, flush = True, lock = True):
        """
        Like protocols.Transport.login(), but makes sure to
        lock/release the account while it is used.
        If an account is not given, one is acquired from the account
        manager.
        Returns the account that was used to log in.

        @type  account: Account
        @param account: The account to use for logging in.
        @type  flush: bool
        @param flush: Whether to flush the last prompt from the buffer.
        @type  lock: bool
        @param lock: Whether to lock the account while logging in.
        @rtype:  Account
        @return: The account that was used to log in.
        """
        account = self._acquire_account(account, lock)
        self._track_account(account)

        try:
            self.transport.login(account, flush = flush)
        finally:
            if lock:
                self._release_account(account)
            self._untrack_accounts()
        return account

    def authenticate(self, account = None, flush = True, lock = True):
        """
        Like protocols.Transport.authenticate(), but makes sure to
        lock/release the account while it is used.
        If an account is not given, one is acquired from the account
        manager.
        Returns the account that was used to log in.

        @type  account: Account
        @param account: The account to use for logging in.
        @type  flush: bool
        @param flush: Whether to flush the last prompt from the buffer.
        @type  lock: bool
        @param lock: Whether to lock the account while logging in.
        @rtype:  Account
        @return: The account that was used to log in.
        """
        account = self._acquire_account(account, lock)
        self._track_account(account)

        try:
            self.transport.authenticate(account, flush = flush)
        finally:
            if lock:
                self._release_account(account)
            self._untrack_accounts()
        return account

    def app_authenticate(self, account = None, flush = True, lock = True):
        """
        Like protocols.Transport.app_authenticate(), but makes sure to
        lock/release the account while it is used.
        If an account is not given, one is acquired from the account
        manager.
        Returns the account that was used to log in.

        @type  account: Account
        @param account: The account to use for logging in.
        @type  flush: bool
        @param flush: Whether to flush the last prompt from the buffer.
        @type  lock: bool
        @param lock: Whether to lock the account while logging in.
        @rtype:  Account
        @return: The account that was used to log in.
        """
        account = self._acquire_account(account, lock)
        self._track_account(account)

        try:
            self.transport.app_authenticate(account, flush = flush)
        finally:
            if lock:
                self._release_account(account)
            self._untrack_accounts()
        return account

    def app_authorize(self, account = None, flush = True, lock = True):
        """
        Like app_authenticate(), but uses the authorization password instead.

        @type  account: Account
        @param account: The account to use for logging in.
        @type  flush: bool
        @param flush: Whether to flush the last prompt from the buffer.
        @type  lock: bool
        @param lock: Whether to lock the account while logging in.
        @rtype:  Account
        @return: The account that was used to log in.
        """
        account = self._acquire_account(account, lock)
        self._track_account(account)

        try:
            self.transport.app_authorize(account, flush = flush)
        finally:
            if lock:
                self._release_account(account)
            self._untrack_accounts()
        return account

    def auto_app_authorize(self,
                           account  = None,
                           flush    = True,
                           lock     = True):
        """
        Executes a command on the remote host that causes an authorization
        procedure to be started, then authorizes using app_authorize().
        For the meaning of the account, flush, and lock arguments see
        app_authorize().
        If the password argument is given, the given password is used
        instead of the given account.

        Depending on the detected operating system of the remote host the
        following commands are started:

          - on IOS, the "enable" command is executed.
          - nothing on other operating systems yet.

        Returns the account that was used to log in.

        @type  account: Account
        @param account: The account to use for logging in.
        @type  flush: bool
        @param flush: Whether to flush the last prompt from the buffer.
        @type  lock: bool
        @param lock: Whether to lock the account while logging in.
        @rtype:  Account
        @return: The account that was used to log in.
        """
        os       = self.guess_os()
        account  = self._acquire_account(account, lock)
        self._track_account(account)

        try:
            self.transport.auto_app_authorize(account, flush = flush)
        finally:
            if lock:
                self._release_account(account)
            self._untrack_accounts()
        return account
