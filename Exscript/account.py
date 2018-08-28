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
Manages user accounts.
"""
from builtins import object
import multiprocessing
from collections import deque, defaultdict
from .util.cast import to_list
from .util.event import Event
from .util.impl import Context


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
        :type  key: Exscript.PrivateKey
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

        :rtype:  Exscript.PrivateKey|None
        :return: A key object.
        """
        return self.key


class AccountProxy(object):

    """
    An object that has a 1:1 relation to an account object in another
    process.
    """

    def __init__(self, parent):
        """
        Constructor.

        :type parent: multiprocessing.Connection
        :param parent: A pipe to the associated account manager.
        """
        self.parent = parent
        self.account_hash = None
        self.host = None
        self.user = None
        self.password = None
        self.authorization_password = None
        self.key = None

    @staticmethod
    def for_host(parent, host):
        """
        Returns a new AccountProxy that has an account acquired. The
        account is chosen based on what the connected AccountManager
        selects for the given host.
        """
        account = AccountProxy(parent)
        account.host = host
        if account.acquire():
            return account
        return None

    @staticmethod
    def for_account_hash(parent, account_hash):
        """
        Returns a new AccountProxy that acquires the account with the
        given hash, if such an account is known to the account manager.
        It is an error if the account manager does not have such an
        account.
        """
        account = AccountProxy(parent)
        account.account_hash = account_hash
        if account.acquire():
            return account
        return None

    @staticmethod
    def for_random_account(parent):
        """
        Returns a new AccountProxy that has an account acquired. The
        account is chosen by the connected AccountManager.
        """
        account = AccountProxy(parent)
        if account.acquire():
            return account
        return None

    def __hash__(self):
        """
        Returns the hash of the currently acquired account.
        """
        return self.account_hash

    def __enter__(self):
        """
        Like :class:`acquire()`.
        """
        return self.acquire()

    def __exit__(self, thetype, value, traceback):
        """
        Like :class:`release()`.
        """
        return self.release()

    def context(self):
        """
        When you need a 'with' context for an already-acquired account.
        """
        return Context(self)

    def acquire(self):
        """
        Locks the account. Returns True on success, False if the account
        is thread-local and must not be locked.
        """
        if self.host:
            self.parent.send(('acquire-account-for-host', self.host))
        elif self.account_hash:
            self.parent.send(('acquire-account-from-hash', self.account_hash))
        else:
            self.parent.send(('acquire-account'))

        response = self.parent.recv()
        if isinstance(response, Exception):
            raise response
        if response is None:
            return False

        self.account_hash, \
            self.user, \
            self.password, \
            self.authorization_password, \
            self.key = response
        return True

    def release(self):
        """
        Unlocks the account.
        """
        self.parent.send(('release-account', self.account_hash))

        response = self.parent.recv()
        if isinstance(response, Exception):
            raise response

        if response != 'ok':
            raise ValueError('unexpected response: ' + repr(response))

    def get_name(self):
        """
        Returns the name of the account.

        :rtype:  string
        :return: The account name.
        """
        return self.user

    def get_password(self):
        """
        Returns the password of the account.

        :rtype:  string
        :return: The account password.
        """
        return self.password

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

        :rtype:  Exscript.PrivateKey|None
        :return: A key object.
        """
        return self.key


class LoggerProxy(object):

    """
    An object that has a 1:1 relation to a Logger object in another
    process.
    """

    def __init__(self, parent, logger_id):
        """
        Constructor.

        :type  parent: multiprocessing.Connection
        :param parent: A pipe to the associated pipe handler.
        """
        self.parent = parent
        self.logger_id = logger_id

    def add_log(self, job_id, name, attempt):
        self.parent.send(('log-add', (self.logger_id, job_id, name, attempt)))
        response = self.parent.recv()
        if isinstance(response, Exception):
            raise response
        return response

    def log(self, job_id, message):
        self.parent.send(('log-message', (self.logger_id, job_id, message)))

    def log_aborted(self, job_id, exc_info):
        self.parent.send(('log-aborted', (self.logger_id, job_id, exc_info)))

    def log_succeeded(self, job_id):
        self.parent.send(('log-succeeded', (self.logger_id, job_id)))


class AccountPool(object):

    """
    This class manages a collection of available accounts.
    """

    def __init__(self, accounts=None):
        """
        Constructor.

        :type  accounts: Account|list[Account]
        :param accounts: Passed to add_account()
        """
        self.accounts = set()
        self.unlocked_accounts = deque()
        self.owner2account = defaultdict(list)
        self.account2owner = dict()
        self.unlock_cond = multiprocessing.Condition(multiprocessing.RLock())
        if accounts:
            self.add_account(accounts)

    def _on_account_acquired(self, account):
        with self.unlock_cond:
            if account not in self.accounts:
                msg = 'attempt to acquire unknown account %s' % account
                raise Exception(msg)
            if account not in self.unlocked_accounts:
                raise Exception('account %s is already locked' % account)
            self.unlocked_accounts.remove(account)
            self.unlock_cond.notify_all()
        return account

    def _on_account_released(self, account):
        with self.unlock_cond:
            if account not in self.accounts:
                msg = 'attempt to acquire unknown account %s' % account
                raise Exception(msg)
            if account in self.unlocked_accounts:
                raise Exception('account %s should be locked' % account)
            self.unlocked_accounts.append(account)
            owner = self.account2owner.get(account)
            if owner is not None:
                self.account2owner.pop(account)
                self.owner2account[owner].remove(account)
            self.unlock_cond.notify_all()
        return account

    def get_account_from_hash(self, account_hash):
        """
        Returns the account with the given hash, or None if no such
        account is included in the account pool.
        """
        for account in self.accounts:
            if account.__hash__() == account_hash:
                return account
        return None

    def has_account(self, account):
        """
        Returns True if the given account exists in the pool, returns False
        otherwise.

        :type  account: Account
        :param account: The account object.
        """
        return account in self.accounts

    def add_account(self, accounts):
        """
        Adds one or more account instances to the pool.

        :type  accounts: Account|list[Account]
        :param accounts: The account to be added.
        """
        with self.unlock_cond:
            for account in to_list(accounts):
                account.acquired_event.listen(self._on_account_acquired)
                account.released_event.listen(self._on_account_released)
                self.accounts.add(account)
                self.unlocked_accounts.append(account)
            self.unlock_cond.notify_all()

    def _remove_account(self, accounts):
        """
        :type  accounts: Account|list[Account]
        :param accounts: The accounts to be removed.
        """
        for account in to_list(accounts):
            if account not in self.accounts:
                msg = 'attempt to remove unknown account %s' % account
                raise Exception(msg)
            if account not in self.unlocked_accounts:
                raise Exception('account %s should be unlocked' % account)
            account.acquired_event.disconnect(self._on_account_acquired)
            account.released_event.disconnect(self._on_account_released)
            self.accounts.remove(account)
            self.unlocked_accounts.remove(account)

    def reset(self):
        """
        Removes all accounts.
        """
        with self.unlock_cond:
            for owner in self.owner2account:
                self.release_accounts(owner)
            self._remove_account(self.accounts.copy())
            self.unlock_cond.notify_all()

    def get_account_from_name(self, name):
        """
        Returns the account with the given name.

        :type  name: string
        :param name: The name of the account.
        """
        for account in self.accounts:
            if account.get_name() == name:
                return account
        return None

    def n_accounts(self):
        """
        Returns the number of accounts that are currently in the pool.
        """
        return len(self.accounts)

    def acquire_account(self, account=None, owner=None):
        """
        Waits until an account becomes available, then locks and returns it.
        If an account is not passed, the next available account is returned.

        :type  account: Account
        :param account: The account to be acquired, or None.
        :type  owner: object
        :param owner: An optional descriptor for the owner.
        :rtype:  :class:`Account`
        :return: The account that was acquired.
        """
        with self.unlock_cond:
            if len(self.accounts) == 0:
                raise ValueError('account pool is empty')

            if account:
                # Specific account requested.
                while account not in self.unlocked_accounts:
                    self.unlock_cond.wait()
                self.unlocked_accounts.remove(account)
            else:
                # Else take the next available one.
                while len(self.unlocked_accounts) == 0:
                    self.unlock_cond.wait()
                account = self.unlocked_accounts.popleft()

            if owner is not None:
                self.owner2account[owner].append(account)
                self.account2owner[account] = owner
            account.acquire(False)
            self.unlock_cond.notify_all()
            return account

    def release_accounts(self, owner):
        """
        Releases all accounts that were acquired by the given owner.

        :type  owner: object
        :param owner: The owner descriptor as passed to acquire_account().
        """
        with self.unlock_cond:
            for account in self.owner2account[owner]:
                self.account2owner.pop(account)
                account.release(False)
                self.unlocked_accounts.append(account)
            self.owner2account.pop(owner)
            self.unlock_cond.notify_all()


class AccountManager(object):

    """
    Keeps track of available user accounts and assigns them to the
    worker threads.
    """

    def __init__(self):
        """
        Constructor.
        """
        self.default_pool = None
        self.pools = None
        self.reset()

    def reset(self):
        """
        Removes all account pools.
        """
        self.default_pool = AccountPool()
        self.pools = []

    def add_pool(self, pool, match=None):
        """
        Adds a new account pool. If the given match argument is
        None, the pool the default pool. Otherwise, the match argument is
        a callback function that is invoked to decide whether or not the
        given pool should be used for a host.

        When Exscript logs into a host, the account is chosen in the following
        order:

            # Exscript checks whether an account was attached to the
            :class:`Host` object using :class:`Host.set_account()`), and uses that.

            # If the :class:`Host` has no account attached, Exscript walks
            through all pools that were passed to :class:`Queue.add_account_pool()`.
            For each pool, it passes the :class:`Host` to the function in the
            given match argument. If the return value is True, the account
            pool is used to acquire an account.
            (Accounts within each pool are taken in a round-robin
            fashion.)

            # If no matching account pool is found, an account is taken
            from the default account pool.

            # Finally, if all that fails and the default account pool
            contains no accounts, an error is raised.

        Example usage::

            def do_nothing(conn):
                conn.autoinit()

            def use_this_pool(host):
                return host.get_name().startswith('foo')

            default_pool = AccountPool()
            default_pool.add_account(Account('default-user', 'password'))

            other_pool = AccountPool()
            other_pool.add_account(Account('user', 'password'))

            queue = Queue()
            queue.account_manager.add_pool(default_pool)
            queue.account_manager.add_pool(other_pool, use_this_pool)

            host = Host('localhost')
            queue.run(host, do_nothing)

        In the example code, the host has no account attached. As a result,
        the queue checks whether use_this_pool() returns True. Because the
        hostname does not start with 'foo', the function returns False, and
        Exscript takes the 'default-user' account from the default pool.

        :type  pool: AccountPool
        :param pool: The account pool that is added.
        :type  match: callable
        :param match: A callback to check if the pool should be used.
        """
        if match is None:
            self.default_pool = pool
        else:
            self.pools.append((match, pool))

    def add_account(self, account):
        """
        Adds the given account to the default account pool that Exscript uses
        to log into all hosts that have no specific :class:`Account` attached.

        :type  account: Account
        :param account: The account that is added.
        """
        self.default_pool.add_account(account)

    def get_account_from_hash(self, account_hash):
        """
        Returns the account with the given hash, if it is contained in any
        of the pools. Returns None otherwise.

        :type  account_hash: str
        :param account_hash: The hash of an account object.
        """
        for _, pool in self.pools:
            account = pool.get_account_from_hash(account_hash)
            if account is not None:
                return account
        return self.default_pool.get_account_from_hash(account_hash)

    def acquire_account(self, account=None, owner=None):
        """
        Acquires the given account. If no account is given, one is chosen
        from the default pool.

        :type  account: Account
        :param account: The account that is added.
        :type  owner: object
        :param owner: An optional descriptor for the owner.
        :rtype:  :class:`Account`
        :return: The account that was acquired.
        """
        if account is not None:
            for _, pool in self.pools:
                if pool.has_account(account):
                    return pool.acquire_account(account, owner)

            if not self.default_pool.has_account(account):
                # The account is not in any pool.
                account.acquire()
                return account

        return self.default_pool.acquire_account(account, owner)

    def acquire_account_for(self, host, owner=None):
        """
        Acquires an account for the given host and returns it.
        The host is passed to each of the match functions that were
        passed in when adding the pool. The first pool for which the
        match function returns True is chosen to assign an account.

        :type  host: :class:`Host`
        :param host: The host for which an account is acquired.
        :type  owner: object
        :param owner: An optional descriptor for the owner.
        :rtype:  :class:`Account`
        :return: The account that was acquired.
        """
        # Check whether a matching account pool exists.
        for match, pool in self.pools:
            if match(host) is True:
                return pool.acquire_account(owner=owner)

        # Else, choose an account from the default account pool.
        return self.default_pool.acquire_account(owner=owner)

    def release_accounts(self, owner):
        """
        Releases all accounts that were acquired by the given owner.

        :type  owner: object
        :param owner: The owner descriptor as passed to acquire_account().
        """
        for _, pool in self.pools:
            pool.release_accounts(owner)
        self.default_pool.release_accounts(owner)
