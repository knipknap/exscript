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
from Exscript.util.impl import Context

class AccountProxy(object):
    """
    An object that has a 1:1 relation to an account object in another
    process.
    """
    def __init__(self, parent):
        """
        Constructor.

        @type  parent: multiprocessing.Connection
        @param parent: A pipe to the associated account manager.
        """
        self.parent                 = parent
        self.account_hash           = None
        self.host_hash              = None
        self.user                   = None
        self.password               = None
        self.authorization_password = None
        self.key                    = None
        self.thread_local           = False

    @staticmethod
    def for_host_hash(parent, host_hash):
        account = AccountProxy(parent)
        account.host_hash = host_hash
        account.acquire()
        return account

    @staticmethod
    def for_account_hash(parent, account_hash):
        account = AccountProxy(parent)
        account.account_hash = account_hash
        account.acquire()
        return account

    @staticmethod
    def for_random_account(parent):
        account = AccountProxy(parent)
        account.acquire()
        return account

    def __hash__(self):
        return self.account_hash

    def __enter__(self):
        return self.acquire()

    def __exit__(self, thetype, value, traceback):
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
        if self.thread_local:
            return False
        if self.host_hash:
            self.parent.send(('acquire-account-for-host', self.host_hash))
        else:
            self.parent.send(('acquire-account', self.account_hash))

        response = self.parent.recv()
        if isinstance(response, Exception):
            raise response
        if response is None:
            self.thread_local = True
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
        if self.thread_local:
            return False
        self.parent.send(('release-account', self.account_hash))

        response = self.parent.recv()
        if isinstance(response, Exception):
            raise response

        if response != 'ok':
            raise ValueError('unexpected response: ' + repr(response))

    def get_name(self):
        """
        Returns the name of the account.

        @rtype:  string
        @return: The account name.
        """
        return self.user

    def get_password(self):
        """
        Returns the password of the account.

        @rtype:  string
        @return: The account password.
        """
        return self.password

    def get_authorization_password(self):
        """
        Returns the authorization password of the account.

        @rtype:  string
        @return: The account password.
        """
        return self.authorization_password or self.password

    def get_key(self):
        """
        Returns the key of the account, if any.

        @rtype:  PrivateKey|None
        @return: A key object.
        """
        return self.key
