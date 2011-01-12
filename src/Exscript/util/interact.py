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
Tools for interacting with the user on the command line.
"""
import getpass
from Exscript import Account

def get_user():
    """
    Prompts the user for his login name, defaulting to the USER environment
    variable. Returns a string containing the username.
    May throw an exception if EOF is given by the user.

    @rtype:  string
    @return: A username.
    """
    # Read username and password.
    try:
        env_user = getpass.getuser()
    except KeyError:
        env_user = ''
    if env_user is None or env_user == '':
        user = raw_input('Please enter your user name: ')
    else:
        user = raw_input('Please enter your user name [%s]: ' % env_user)
        if user == '':
            user = env_user
    return user

def get_login():
    """
    Prompts the user for the login name using get_user(), and also asks for
    the password.
    Returns a tuple containing the username and the password.
    May throw an exception if EOF is given by the user.

    @rtype:  (string, string)
    @return: A tuple containing the username and the password.
    """
    user     = get_user()
    password = getpass.getpass('Please enter your password: ')
    return user, password

def read_login():
    """
    Like get_login(), but returns an Account object.

    @rtype:  Account
    @return: A new account.
    """
    user, password = get_login()
    return Account(user, password)
