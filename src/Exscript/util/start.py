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
from Exscript import Exscript
from interact import read_login

def run(users, hosts, func, *args, **kwargs):
    """
    Convenience function that creates an Exscript instance, adds
    the given accounts, and call Exscript.run() with the given
    hosts and function as an argument.

    @type  users: Account|list[Account]
    @param users: The account(s) to use for logging in.
    @type  hosts: Host|list[Host]
    @param hosts: A list of Host objects.
    @type  func: function
    @param func: The callback function.
    @type  args: list
    @param args: Passed on to the callback.
    @type  kwargs: dict
    @param kwargs: Passed on to the callback.
    """
    exscript = Exscript(**kwargs)
    exscript.add_account(users)
    exscript.run(hosts, func, *args, **kwargs)

def quickrun(hosts, func, *data, **kwargs):
    """
    A wrapper around run() that creates the account by asking the user
    for entering his login information.

    @type  hosts: Host|list[Host]
    @param hosts: A list of Host objects.
    @type  func: function
    @param func: The callback function.
    @type  args: list
    @param args: Passed on to the callback.
    @type  kwargs: dict
    @param kwargs: Passed on to the callback.
    """
    run(read_login(), hosts, func, *data, **kwargs)
