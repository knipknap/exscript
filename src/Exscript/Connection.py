# Copyright (C) 2007-2009 Samuel Abels.
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
import threading, os.path

True  = 1
False = 0

class Connection(object):
    """
    This class is a decorator for protocols.Transport objects that
    adds thread safety by adding locking to the authenticate() and
    authorize() functions.
    It also provides access to the associated Queue and Host instances.

    For complete documentation, please refer to the protocols.Transport
    documentation.
    """

    def __init__(self, queue, host, **kwargs):
        """
        Do not call directly; Exscript creates the connection for you and
        passes it to the function that is invoked by Queue.run().

        @type  queue: Queue
        @param queue: The associated Queue instance.
        @type  host: Host
        @param host: The host on which the job is executed.
        @type  kwargs: dict
        @param kwargs: For a list of supported options please check the
                       protocol adapter API documentation.
        """
        # Since we override setattr below, we can't access our properties
        # directly.
        self.__dict__['queue']        = queue
        self.__dict__['host']         = host
        self.__dict__['last_account'] = None

        # Define protocol specific options.
        protocol = queue._get_protocol_from_name(host.get_protocol())
        if host.get_protocol() == 'ssh1':
            kwargs['ssh_version'] = 1
        elif host.get_protocol() == 'ssh2':
            kwargs['ssh_version'] = 2
        else:
            kwargs['ssh_version'] = None
        if host.get_tcp_port() is not None:
            kwargs['port'] = host.get_tcp_port()

        # Create an instance of the protocol adapter.
        transport = protocol(**kwargs)
        self.__dict__['transport'] = transport
        if host.get_protocol() == 'pseudo':
            filename = host.get_address()
            hostname = os.path.basename(filename)
            host.set_name(hostname)
            transport.load_command_handler_from_file(filename)


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
        account.signal_emit('otp_requested', account, key, seq)

    def _acquire_account(self, account = None, lock = True):
        if account and lock:
            account.acquire()
        elif account:
            pass
        elif self.last_account and lock:
            account = self.last_account
            account.acquire()
        elif self.last_account:
            account = self.last_account
        elif lock:
            account = self.get_account_manager().acquire_account()
        else:
            raise Exception('Non-locking shared accounts unsupported.')
        self.last_account = account
        self.transport.signal_connect('otp_requested',
                                      self._on_otp_requested,
                                      account)
        return account

    def _release_account(self, account = None):
        self.transport.signal_disconnect('otp_requested',
                                         self._on_otp_requested)
        if account == self.last_account:
            account = None
        if account:
            account.release()
        elif self.last_account:
            self.last_account.release()
            self.last_account = None
        else:
            raise Exception('Attempt to relase a released account.')

    def get_queue(self):
        """
        Returns the associated Queue instance.

        @rtype:  Queue
        @return: The associated Queue instance.
        """
        return self.queue

    def get_account_manager(self):
        """
        Returns the associated account manager.

        @rtype:  AccountManager
        @return: The associated account manager.
        """
        return self.queue.account_manager

    def get_host(self):
        """
        Returns the host on which the job is performed.

        @rtype:  Host
        @return: The Host instance.
        """
        return self.host

    def open(self):
        """
        Opens the connection to the remote host.
        """
        if not self.transport.connect(self.host.get_address(),
                                      self.host.get_tcp_port()):
            raise Exception('Connection failed.')

    def authenticate(self, account = None, wait = False, lock = True):
        """
        Like protocols.Transport.authenticate(), but makes sure to
        lock/release the account while it is used.
        If an account is not given, one is acquired from the account
        manager.
        Returns the account that was used to log in.

        @type  account: Account
        @param account: The account to use for logging in.
        @type  wait: bool
        @param wait: Whether to wait for a prompt after sending the password.
        @type  lock: bool
        @param lock: Whether to lock the account while logging in.
        @rtype:  Account
        @return: The account that was used to log in.
        """
        account  = self._acquire_account(account, lock)
        key_file = account.options.get('ssh_key_file')

        try:
            self.transport.authenticate(account.get_name(),
                                        account.get_password(),
                                        wait     = wait,
                                        key_file = key_file)
        except:
            if lock:
                self._release_account(account)
            raise
        if lock:
            self._release_account(account)
        return account

    def authorize(self, account = None, wait = False, lock = True):
        """
        Like authenticate(), but uses the authorization password instead.

        @type  account: Account
        @param account: The account to use for logging in.
        @type  wait: bool
        @param wait: Whether to wait for a prompt after sending the password.
        @type  lock: bool
        @param lock: Whether to lock the account while logging in.
        @rtype:  Account
        @return: The account that was used to log in.
        """
        account  = self._acquire_account(account, lock)
        key_file = account.options.get('ssh_key_file')
        password = account.get_authorization_password()

        try:
            self.transport.authorize(password, wait = wait)
        except:
            if lock:
                self._release_account(account)
            raise
        if lock:
            self._release_account(account)
        return account

    def auto_authorize(self,
                       account  = None,
                       wait     = True,
                       lock     = True,
                       password = None):
        """
        Executes a command on the remote host that causes an authorization
        procedure to be started, then authorizes using authorize().
        For the meaning of the account, wait, and lock arguments see
        authorize().
        If the password argument is given, the given password is used
        instead of the given account.

        Depending on the detected operating system of the remote host the
        following commands are started:

          - on IOS, the "enable" command is executed.
          - nothing on other operating systems yet.

        Returns the account that was used to log in.

        @type  account: Account
        @param account: The account to use for logging in.
        @type  wait: bool
        @param wait: Whether to wait for a prompt after sending the password.
        @type  lock: bool
        @param lock: Whether to lock the account while logging in.
        @type  password: string
        @param password: The optional password to use.
        @rtype:  Account
        @return: The account that was used to log in.
        """
        os       = self.guess_os()
        account  = self._acquire_account(account, lock)
        command  = {'ios':    'enable\r',
                    'one_os': 'enable\r',
                    'junos':  None,
                    'ios_xr': None}.get(os)

        if password is None:
            password = account.get_authorization_password()

        try:
            if command:
                self.send(command)
                self.transport.authorize(password, wait = wait)
        except:
            if lock:
                self._release_account(account)
            raise
        if lock:
            self._release_account(account)
        return account
