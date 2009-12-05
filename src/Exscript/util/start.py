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
from Exscript import Queue
from interact import read_login

def run(users, hosts, func, **kwargs):
    """
    Convenience function that creates an Exscript.Queue instance, adds
    the given accounts, and calls Queue.run() with the given
    hosts and function as an argument.

    If you also want to pass arguments to the given function, you may use
    util.decorator.bind_args() like this::

      def my_callback(conn, my_arg, **kwargs):
          print my_arg, kwargs.get('foo')

      run(account,
          host,
          bind_args(my_callback, 'hello', foo = 'world'),
          max_threads = 10)

    @type  users: Account|list[Account]
    @param users: The account(s) to use for logging in.
    @type  hosts: Host|list[Host]
    @param hosts: A list of Host objects.
    @type  func: function
    @param func: The callback function.
    @type  kwargs: dict
    @param kwargs: Passed to the Exscript.Queue constructor.
    """
    exscript = Queue(*args, **kwargs)
    exscript.add_account(users)
    exscript.run(hosts, func)

def quickrun(hosts, func, **kwargs):
    """
    A wrapper around run() that creates the account by asking the user
    for entering his login information.

    @type  hosts: Host|list[Host]
    @param hosts: A list of Host objects.
    @type  func: function
    @param func: The callback function.
    @type  kwargs: dict
    @param kwargs: Passed to the Exscript.Queue constructor.
    """
    run(read_login(), hosts, func, **kwargs)
