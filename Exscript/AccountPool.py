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
A collection of user accounts.
"""
import multiprocessing
from collections import deque, defaultdict
from Exscript.util.cast import to_list

class AccountPool(object):
    """
    This class manages a collection of available accounts.
    """

    def __init__(self, accounts = None):
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

    def acquire_account(self, account = None, owner = None):
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
