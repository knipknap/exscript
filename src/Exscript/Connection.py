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

class Connection(object):
    """
    This class is a decorator for protocols.Protocol objects that
    adds thread safety by adding locking to the authenticate() and
    authorize() functions.
    It also provides access to the associated Host instance.

    For complete documentation, please refer to the protocols.Protocol
    documentation.
    """

    def __init__(self, action, protocol):
        """
        Do not call directly; Exscript creates the connection for you and
        passes it to the function that is invoked by Queue.run().

        @type  action: HostAction
        @param action: The associated HostAction instance.
        @type  protocol: L{protocols.Protocol}
        @param protocol: The Protocol object that is decorated.
        """
        # Since we override setattr below, we can't access our properties
        # directly.
        self.__dict__['action']   = action
        self.__dict__['protocol'] = protocol

    def __copy__(self):
        """
        Overwritten to return the very same object instead of copying the
        stream, because copying a network connection is impossible.

        @rtype:  Protocol
        @return: self
        """
        return self

    def __deepcopy__(self, memo):
        """
        Overwritten to return the very same object instead of copying the
        stream, because copying a network connection is impossible.

        @type  memo: object
        @param memo: Please refer to Python's standard library documentation.
        @rtype:  Protocol
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
            setattr(self.protocol, name, value)

    def __getattr__(self, name):
        """
        Overwritten to proxy any calls to the associated protocol adapter
        (decorator pattern).

        @type  name: string
        @param name: The attribute name.
        @rtype:  object
        @return: Whatever the protocol adapter returns.
        """
        if name in self.__dict__.keys():
            return self.__dict__[name]
        return getattr(self.protocol, name)

    def get_host(self):
        """
        Returns the host on which the job is performed.

        @rtype:  Host
        @return: The Host instance.
        """
        return self.action.get_host()

    def add_monitor(self, pattern, callback):
        """
        Like L{protocols.Protocol.add_monitor}.
        """
        def the_callback(conn, index, match):
            return callback(self, index, match)
        return self.protocol.add_monitor(pattern, the_callback)

    def connect(self):
        """
        Opens the connection to the remote host.
        """
        if not self.protocol.connect(self.get_host().get_address(),
                                     self.get_host().get_tcp_port()):
            raise Exception('Connection failed.')

    def login(self, account = None, flush = True):
        """
        Like protocols.Protocol.login(), but makes sure to
        lock/release the account while it is used.
        If an account is not given, one is acquired from the account
        manager.
        Returns the account that was used to log in.

        @type  account: Account|None
        @param account: The account to use for logging in.
        @type  flush: bool
        @param flush: Whether to flush the last prompt from the buffer.
        @rtype:  AccountProxy
        @return: The account that was used to log in.
        """
        with self.action.acquire_account(account).context() as account:
            self.protocol.login(account, flush = flush)
        return account

    def authenticate(self, account = None, flush = True):
        """
        Like protocols.Protocol.authenticate(), but makes sure to
        lock/release the account while it is used.
        If an account is not given, one is acquired from the account
        manager.
        Returns the account that was used to log in.

        @type  account: Account|None
        @param account: The account to use for logging in.
        @type  flush: bool
        @param flush: Whether to flush the last prompt from the buffer.
        @rtype:  AccountProxy
        @return: The account that was used to log in.
        """
        with self.action.acquire_account(account).context() as account:
            self.protocol.authenticate(account, flush = flush)
        return account

    def protocol_authenticate(self, account = None):
        """
        Like protocols.Protocol.protocol_authenticate(), but makes sure to
        lock/release the account while it is used.
        If an account is not given, one is acquired from the account
        manager.
        Returns the account that was used to log in.

        @type  account: Account|None
        @param account: The account to use for logging in.
        @rtype:  AccountProxy
        @return: The account that was used to log in.
        """
        with self.action.acquire_account(account).context() as account:
            self.protocol.protocol_authenticate(account)
        return account

    def app_authenticate(self, account = None, flush = True):
        """
        Like protocols.Protocol.app_authenticate(), but makes sure to
        lock/release the account while it is used.
        If an account is not given, one is acquired from the account
        manager.
        Returns the account that was used to log in.

        @type  account: Account|None
        @param account: The account to use for logging in.
        @type  flush: bool
        @param flush: Whether to flush the last prompt from the buffer.
        @rtype:  AccountProxy
        @return: The account that was used to log in.
        """
        with self.action.acquire_account(account).context() as account:
            self.protocol.app_authenticate(account, flush = flush)
        return account

    def app_authorize(self, account = None, flush = True):
        """
        Like app_authenticate(), but uses the authorization password instead.

        @type  account: Account|None
        @param account: The account to use for logging in.
        @type  flush: bool
        @param flush: Whether to flush the last prompt from the buffer.
        @rtype:  AccountProxy
        @return: The account that was used to log in.
        """
        with self.action.acquire_account(account).context() as account:
            self.protocol.app_authorize(account, flush = flush)
        return account

    def auto_app_authorize(self, account = None, flush = True):
        """
        Executes a command on the remote host that causes an authorization
        procedure to be started, then authorizes using app_authorize().
        For the meaning of the account and flush arguments see
        app_authorize().
        If the password argument is given, the given password is used
        instead of the given account.

        Depending on the detected operating system of the remote host the
        following commands are started:

          - on IOS, the "enable" command is executed.
          - nothing on other operating systems yet.

        Returns the account that was used to log in.

        @type  account: Account|None
        @param account: The account to use for logging in.
        @type  flush: bool
        @param flush: Whether to flush the last prompt from the buffer.
        @rtype:  AccountProxy
        @return: The account that was used to log in.
        """
        with self.action.acquire_account(account).context() as account:
            self.protocol.auto_app_authorize(account, flush = flush)
        return account
