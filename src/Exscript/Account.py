# Copyright (C) 2007 Samuel Abels, http://debain.org
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

class Account(object):
    """
    This class manages available accounts.
    """

    def __init__(self, name, password, password2 = None, **kwargs):
        """
        Constructor.
        """
        self.manager                = None
        self.name                   = name
        self.password               = password
        self.authorization_password = password2
        self.options                = kwargs
        self.lock                   = threading.Lock()


    def _add_notify(self, manager):
        self.manager = manager


    def acquire(self):
        """
        Locks the account.

        @rtype:  Account
        @return: The locked account.
        """
        self.lock.acquire()


    def release(self):
        """
        Unlocks the account.

        @rtype:  Account
        @return: The locked account.
        """
        self.manager.release_account(self)
        self.lock.release()


    def get_name(self):
        """
        Returns the name of the account.

        @rtype:  string
        @return: The account name.
        """
        return self.name


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
