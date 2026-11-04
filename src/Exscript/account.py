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

import multiprocessing
from collections import defaultdict, deque
from collections.abc import Callable, Hashable, Iterable
from types import TracebackType
from typing import TYPE_CHECKING, Self, cast

from .key import PrivateKey
from .logger import Log
from .util.cast import to_list
from .util.event import Event
from .util.impl import Context

if TYPE_CHECKING:
    # _ConnectionBase is the common base class of the pipe connections on
    # POSIX (Connection) and on Windows (PipeConnection).
    from multiprocessing.connection import _ConnectionBase

    from .host import Host


class Account:
    """
    This class represents a user account.
    """

    def __init__(
        self,
        name: str,
        password: str | None = '',
        password2: str | None = None,
        key: PrivateKey | None = None,
        needs_lock: bool = True,
    ) -> None:
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
            Setting `needs_lock` to True drastically degrades performance!

        :type  name: str
        :param name: A username.
        :type  password: str|None
        :param password: The authentication password, or None if it is unknown.
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

    def __repr__(self) -> str:
        return f'{type(self).__name__}({self.name!r})'  # never the passwords

    def __enter__(self) -> Self:
        if self.needs_lock:
            self.acquire()
        return self

    def __exit__(
        self,
        thetype: type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self.needs_lock:
            self.release()

    def context(self) -> Context:
        """
        When you need a 'with' context for an already-acquired account.
        """
        return Context(self)

    def acquire(self, signal: bool = True) -> None:
        """
        Locks the account.
        Method has no effect if the constructor argument `needs_lock`
        was set to False.

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

    def release(self, signal: bool = True) -> None:
        """
        Unlocks the account.
        Method has no effect if the constructor argument `needs_lock`
        was set to False.

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

    def set_name(self, name: str) -> None:
        """
        Changes the name of the account.

        :type  name: string
        :param name: The account name.
        """
        self.name = name
        self.changed_event.emit(self)

    def get_name(self) -> str:
        """
        Returns the name of the account.

        :rtype:  string
        :return: The account name.
        """
        return self.name

    def set_password(self, password: str | None) -> None:
        """
        Changes the password of the account.

        :type  password: string|None
        :param password: The account password, or None if it is unknown.
        """
        self.password = password
        self.changed_event.emit(self)

    def get_password(self) -> str | None:
        """
        Returns the password of the account.

        :rtype:  string|None
        :return: The account password, or None if it is unknown.
        """
        return self.password

    def set_authorization_password(self, password: str | None) -> None:
        """
        Changes the authorization password of the account.

        :type  password: string|None
        :param password: The new authorization password, or None to use the
            authentication password.
        """
        self.authorization_password = password
        self.changed_event.emit(self)

    def get_authorization_password(self) -> str | None:
        """
        Returns the authorization password of the account, or the
        authentication password if no authorization password is set.

        :rtype:  string|None
        :return: The account password.
        """
        return self.authorization_password or self.password

    def get_key(self) -> PrivateKey | None:
        """
        Returns the key of the account, if any.

        :rtype:  Exscript.PrivateKey|None
        :return: A key object.
        """
        return self.key


class AccountProxy:
    """
    An object that has a 1:1 relation to an account object in another
    process.
    """

    def __init__(self, parent: '_ConnectionBase') -> None:
        """
        Constructor.

        :type parent: multiprocessing.Connection
        :param parent: A pipe to the associated account manager.
        """
        self.parent = parent
        self.account_hash: int | None = None
        self.host: Host | None = None
        self.user: str | None = None
        self.password: str | None = None
        self.authorization_password: str | None = None
        self.key: PrivateKey | None = None

    @staticmethod
    def for_host(parent: '_ConnectionBase', host: 'Host') -> 'AccountProxy | None':
        """
        Returns a new AccountProxy that has an account acquired. The
        account is chosen based on what the connected AccountManager
        selects for the given host. Returns None if the account manager
        returns no account.
        """
        account = AccountProxy(parent)
        account.host = host
        if account.acquire():
            return account
        return None

    @staticmethod
    def for_account_hash(parent: '_ConnectionBase', account_hash: int) -> 'AccountProxy | None':
        """
        Returns a new AccountProxy that acquires the account with the
        given hash, if such an account is known to the account manager.
        Returns None if the account manager does not have such an
        account.
        """
        account = AccountProxy(parent)
        account.account_hash = account_hash
        if account.acquire():
            return account
        return None

    @staticmethod
    def for_random_account(parent: '_ConnectionBase') -> 'AccountProxy | None':
        """
        Returns a new AccountProxy that has an account acquired. The
        account is chosen by the connected AccountManager. Returns None
        if the account manager returns no account.
        """
        account = AccountProxy(parent)
        if account.acquire():
            return account
        return None

    def __hash__(self) -> int:
        """
        Returns the hash of the currently acquired account. Until an
        account was acquired, the hash is None, and hash() raises a
        TypeError.
        """
        # account_hash is None until an account is acquired; the cast keeps
        # the int return type that hash() requires.
        return cast(int, self.account_hash)

    def __enter__(self) -> bool:
        """
        Like :class:`acquire()`.
        """
        return self.acquire()

    def __exit__(
        self,
        thetype: type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """
        Like :class:`release()`.
        """
        return self.release()

    def context(self) -> Context:
        """
        When you need a 'with' context for an already-acquired account.
        """
        return Context(self)

    def acquire(self) -> bool:
        """
        Locks the account. Returns True on success, False if the account
        is thread-local and must not be locked.
        """
        if self.host:
            self.parent.send(('acquire-account-for-host', self.host))
        elif self.account_hash:
            self.parent.send(('acquire-account-from-hash', self.account_hash))
        else:
            self.parent.send('acquire-account')

        response = self.parent.recv()
        if isinstance(response, Exception):
            raise response
        if response is None:
            return False

        self.account_hash, self.user, self.password, self.authorization_password, self.key = (
            response
        )
        return True

    def release(self) -> None:
        """
        Unlocks the account.
        """
        self.parent.send(('release-account', self.account_hash))

        response = self.parent.recv()
        if isinstance(response, Exception):
            raise response

        if response != 'ok':
            raise ValueError('unexpected response: ' + repr(response))

    def get_name(self) -> str | None:
        """
        Returns the name of the account.

        :rtype:  string|None
        :return: The account name, or None if no account was acquired.
        """
        return self.user

    def get_password(self) -> str | None:
        """
        Returns the password of the account.

        :rtype:  string|None
        :return: The account password, or None if it is unknown.
        """
        return self.password

    def get_authorization_password(self) -> str | None:
        """
        Returns the authorization password of the account, or the
        authentication password if no authorization password is set.

        :rtype:  string|None
        :return: The account password.
        """
        return self.authorization_password or self.password

    def get_key(self) -> PrivateKey | None:
        """
        Returns the key of the account, if any.

        :rtype:  Exscript.PrivateKey|None
        :return: A key object.
        """
        return self.key


class LoggerProxy:
    """
    An object that has a 1:1 relation to a Logger object in another
    process.
    """

    def __init__(self, parent: '_ConnectionBase', logger_id: int) -> None:
        """
        Constructor.

        :type  parent: multiprocessing.Connection
        :param parent: A pipe to the associated pipe handler.
        :param logger_id: The id() of the Logger in the other process.
        """
        self.parent = parent
        self.logger_id = logger_id

    def add_log(self, job_id: int, name: str, attempt: int) -> Log | None:
        """
        Asks the logger in the other process to create a log for a new
        attempt of the given job.

        :return: A copy of the new log, or None if the logger no longer
            exists.
        """
        self.parent.send(('log-add', (self.logger_id, job_id, name, attempt)))
        response = self.parent.recv()
        if isinstance(response, Exception):
            raise response
        # The pipe returns unpickled objects without a static type.
        return cast(Log | None, response)

    def log(self, job_id: int, message: str) -> None:
        """
        Sends the message to the log of the given job in the other process.
        """
        self.parent.send(('log-message', (self.logger_id, job_id, message)))

    def log_aborted(
        self, job_id: int, exc_info: tuple[type[BaseException], BaseException, str]
    ) -> None:
        """
        Tells the logger in the other process that the given job failed.

        :param exc_info: The exception, as returned by
            :func:`Exscript.util.impl.serializeable_sys_exc_info()`.
        """
        self.parent.send(('log-aborted', (self.logger_id, job_id, exc_info)))

    def log_succeeded(self, job_id: int) -> None:
        """
        Tells the logger in the other process that the given job succeeded.
        """
        self.parent.send(('log-succeeded', (self.logger_id, job_id)))


class AccountPool:
    """
    This class manages a collection of available accounts.
    """

    def __init__(self, accounts: Account | Iterable[Account] | None = None) -> None:
        """
        Constructor.

        :type  accounts: Account|list[Account]
        :param accounts: Passed to add_account()
        """
        self.accounts: set[Account] = set()
        self.unlocked_accounts: deque[Account] = deque()
        self.owner2account: defaultdict[Hashable, list[Account]] = defaultdict(list)
        self.account2owner: dict[Account, Hashable] = dict()
        self.unlock_cond = multiprocessing.Condition(multiprocessing.RLock())
        if accounts:
            self.add_account(accounts)

    def _on_account_acquired(self, account: Account) -> Account:
        """
        Called when the given account was acquired outside of the pool;
        marks it as locked.
        """
        with self.unlock_cond:
            if account not in self.accounts:
                msg = 'attempt to acquire unknown account %s' % account
                raise Exception(msg)
            if account not in self.unlocked_accounts:
                raise Exception('account %s is already locked' % account)
            self.unlocked_accounts.remove(account)
            self.unlock_cond.notify_all()
        return account

    def _on_account_released(self, account: Account) -> Account:
        """
        Called when the given account was released; marks it as unlocked
        and forgets its owner.
        """
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

    def get_account_from_hash(self, account_hash: int) -> Account | None:
        """
        Returns the account with the given hash, or None if no such
        account is included in the account pool.
        """
        for account in self.accounts:
            if account.__hash__() == account_hash:
                return account
        return None

    def has_account(self, account: Account) -> bool:
        """
        Returns True if the given account exists in the pool, returns False
        otherwise.

        :type  account: Account
        :param account: The account object.
        """
        return account in self.accounts

    def add_account(self, accounts: Account | Iterable[Account]) -> None:
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

    def _remove_account(self, accounts: Account | Iterable[Account]) -> None:
        """
        Removes one or more unlocked accounts from the pool and stops
        listening to their events.

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

    def reset(self) -> None:
        """
        Removes all accounts.
        """
        with self.unlock_cond:
            for owner in self.owner2account:
                self.release_accounts(owner)
            self._remove_account(self.accounts.copy())
            self.unlock_cond.notify_all()

    def get_account_from_name(self, name: str) -> Account | None:
        """
        Returns the account with the given name, or None if no such
        account is included in the account pool.

        :type  name: string
        :param name: The name of the account.
        """
        for account in self.accounts:
            if account.get_name() == name:
                return account
        return None

    def n_accounts(self) -> int:
        """
        Returns the number of accounts that are currently in the pool.
        """
        return len(self.accounts)

    def acquire_account(
        self, account: Account | None = None, owner: Hashable | None = None
    ) -> Account:
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

    def release_accounts(self, owner: Hashable) -> None:
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


class AccountManager:
    """
    Keeps track of available user accounts and assigns them to the
    worker threads.
    """

    def __init__(self) -> None:
        """
        Constructor.
        """
        # reset() sets both attributes; the casts are for the type checker.
        self.default_pool: AccountPool = cast(AccountPool, None)
        self.pools: list[tuple[Callable[[Host], bool], AccountPool]] = cast(
            'list[tuple[Callable[[Host], bool], AccountPool]]', None
        )
        self.reset()

    def reset(self) -> None:
        """
        Removes all account pools.
        """
        self.default_pool = AccountPool()
        self.pools = []

    def add_pool(self, pool: AccountPool, match: 'Callable[[Host], bool] | None' = None) -> None:
        """
        Adds a new account pool. If the given match argument is
        None, the pool is the default pool. Otherwise, the match argument is
        a callback function that is invoked to decide whether or not the
        given pool should be used for a host.

        When Exscript logs into a host, the account is chosen in the following
        order:

        #. Exscript checks whether an account was attached to the
           :class:`Host` object using :class:`Host.set_account()`, and uses that.

        #. If the :class:`Host` has no account attached, Exscript walks
           through all pools that were passed to :class:`Queue.add_account_pool()`.
           For each pool, it passes the :class:`Host` to the function in the
           given match argument. If the return value is True, the account
           pool is used to acquire an account.
           (Accounts within each pool are taken in a round-robin
           fashion.)

        #. If no matching account pool is found, an account is taken
           from the default account pool.

        #. Finally, if all that fails and the default account pool
           contains no accounts, an error is raised.

        Example usage::

            def log_in(job, host, conn):
                conn.login()

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
            queue.run(host, log_in)

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

    def add_account(self, account: Account | Iterable[Account]) -> None:
        """
        Adds the given account to the default account pool that Exscript uses
        to log into all hosts that have no specific :class:`Account` attached.

        :type  account: Account|list[Account]
        :param account: The account or accounts that are added.
        """
        self.default_pool.add_account(account)

    def get_account_from_hash(self, account_hash: int) -> Account | None:
        """
        Returns the account with the given hash, if it is contained in any
        of the pools. Returns None otherwise.

        :type  account_hash: int
        :param account_hash: The hash of an account object.
        """
        for _, pool in self.pools:
            account = pool.get_account_from_hash(account_hash)
            if account is not None:
                return account
        return self.default_pool.get_account_from_hash(account_hash)

    def acquire_account(
        self, account: Account | None = None, owner: Hashable | None = None
    ) -> Account:
        """
        Acquires the given account. If no account is given, one is chosen
        from the default pool.

        :type  account: Account
        :param account: The account to be acquired, or None.
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

    def acquire_account_for(self, host: 'Host', owner: Hashable | None = None) -> Account:
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

    def release_accounts(self, owner: Hashable) -> None:
        """
        Releases all accounts that were acquired by the given owner.

        :type  owner: object
        :param owner: The owner descriptor as passed to acquire_account().
        """
        for _, pool in self.pools:
            pool.release_accounts(owner)
        self.default_pool.release_accounts(owner)
