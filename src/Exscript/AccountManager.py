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
import threading
from collections        import deque
from Exscript.util.cast import to_list

class AccountManager(object):
    """
    This class manages a collection of available accounts.
    """

    def __init__(self, accounts = None):
        """
        Constructor.

        @type  accounts: Account|list[Account]
        @param accounts: Passed to add_account()
        """
        self.accounts          = set()
        self.unlocked_accounts = deque()
        self.unlock_cond       = threading.Condition()
        if accounts:
            self.add_account(accounts)

    def _on_account_acquire_before(self, account):
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
            self.unlock_cond.notify_all()
        return account

    def add_account(self, accounts):
        """
        Adds one or more account instances to the pool.

        @type  accounts: Account|list[Account]
        @param accounts: The account to be added.
        """
        with self.unlock_cond:
            for account in to_list(accounts):
                account.acquire_before_event.listen(
                                         self._on_account_acquire_before)
                account.released_event.listen(self._on_account_released)
                self.accounts.add(account)
                self.unlocked_accounts.append(account)
            self.unlock_cond.notify_all()

    def _remove_account(self, accounts):
        """
        Adds one or more account instances to the pool.

        @type  accounts: Account|list[Account]
        @param accounts: The accounts to be removed.
        """
        for account in to_list(accounts):
            if account not in self.accounts:
                msg = 'attempt to remove unknown account %s' % account
                raise Exception(msg)
            if account not in self.unlocked_accounts:
                raise Exception('account %s should be unlocked' % account)
            account.acquire_before_event.disconnect(
                                      self._on_account_acquire_before)
            account.released_event.disconnect(self._on_account_released)
            self.accounts.remove(account)
            self.unlocked_accounts.remove(account)

    def reset(self):
        """
        Removes all accounts.
        """
        with self.unlock_cond:
            self._remove_account(self.accounts.copy())
            self.unlock_cond.notify_all()

    def get_account_from_name(self, name):
        """
        Returns the account with the given name.

        @type  name: string
        @param name: The name of the account.
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

    def _acquire_specific_account(self, account):
        assert account in self.accounts
        account = account.acquire()

    def acquire_account(self, account = None):
        """
        Waits until an account becomes available, then locks and returns it.
        If an account is not passed, the next available account is returned.

        @type  account: Account
        @param account: The account to be acquired, or None.
        @rtype:  Account
        @return: The account to be added.
        """
        if account:
            return self._acquire_specific_account(account)
        assert len(self.accounts) > 0
        with self.unlock_cond:
            while len(self.unlocked_accounts) == 0:
                self.unlock_cond.wait()
            account = self.unlocked_accounts.popleft()
            account._acquire()
        return account

    def release_account(self, account):
        """
        Unlocks a previously locked account.

        @type  account: Account
        @param account: The account to be unlocked.
        """
        account.release()
