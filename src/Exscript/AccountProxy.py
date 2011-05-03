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
        self.host                   = None
        self.user                   = None
        self.password               = None
        self.authorization_password = None
        self.key                    = None

    @staticmethod
    def for_host(parent, host):
        account = AccountProxy(parent)
        account.host = host
        account.acquire()
        return account

    @staticmethod
    def for_account(parent, account):
        account = AccountProxy(parent)
        account.account_hash = account.__hash__()
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
        old_enter = self.__enter__
        old_exit  = self.__exit__
        def exit_context(thetype, value, traceback):
            self.__enter__ = old_enter
            self.__exit__  = old_exit
            self.__exit__(thetype, value, traceback)
        self.__enter__ = lambda: self
        self.__exit__  = exit_context
        return self

    def acquire(self):
        """
        Locks the account.
        """
        if self.account_hash:
            self.parent.send(('acquire-account', self.account_hash))
        elif self.host:
            host = self.host.__copy__()
            self.parent.send(('acquire-account-for-host', host))
        else:
            raise Exception('bug: have neither account nor host')

        response = self.parent.recv()
        if isinstance(response, Exception):
            raise response

        self.account_hash, \
        self.user, \
        self.password, \
        self.authorization_password, \
        self.key = response

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
