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
A remote object that acquires/releases an account via a pipe.
"""
from Exscript.util.impl import Context

class AccountProxy(object):
    """
    An object that has a 1:1 relation to an account object in another
    process.
    """
    def __init__(self, parent):
        """
        Constructor.

        :type  parent: multiprocessing.Connection
        :param parent: A pipe to the associated account manager.
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

        :rtype:  PrivateKey|None
        :return: A key object.
        """
        return self.key
