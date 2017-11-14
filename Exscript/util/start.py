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
Quickstart methods for the Exscript queue.
"""
from __future__ import print_function, absolute_import
from .. import Queue
from .interact import read_login
from .decorator import autologin, autoauthenticate


def run(users, hosts, func, **kwargs):
    """
    Convenience function that creates an Exscript.Queue instance, adds
    the given accounts, and calls Queue.run() with the given
    hosts and function as an argument.

    If you also want to pass arguments to the given function, you may use
    util.decorator.bind() like this::

      def my_callback(job, host, conn, my_arg, **kwargs):
          print(my_arg, kwargs.get('foo'))

      run(account,
          host,
          bind(my_callback, 'hello', foo = 'world'),
          max_threads = 10)

    :type  users: Account|list[Account]
    :param users: The account(s) to use for logging in.
    :type  hosts: Host|list[Host]
    :param hosts: A list of Host objects.
    :type  func: function
    :param func: The callback function.
    :type  kwargs: dict
    :param kwargs: Passed to the Exscript.Queue constructor.
    """
    attempts = kwargs.get("attempts", 1)
    if "attempts" in kwargs:
        del kwargs["attempts"]
    queue = Queue(**kwargs)
    queue.add_account(users)
    queue.run(hosts, func, attempts)
    queue.destroy()


def quickrun(hosts, func, **kwargs):
    """
    A wrapper around run() that creates the account by asking the user
    for entering his login information.

    :type  hosts: Host|list[Host]
    :param hosts: A list of Host objects.
    :type  func: function
    :param func: The callback function.
    :type  kwargs: dict
    :param kwargs: Passed to the Exscript.Queue constructor.
    """
    run(read_login(), hosts, func, **kwargs)


def start(users, hosts, func, only_authenticate=False, **kwargs):
    """
    Like run(), but automatically logs into the host before passing
    the host to the callback function.

    :type  users: Account|list[Account]
    :param users: The account(s) to use for logging in.
    :type  hosts: Host|list[Host]
    :param hosts: A list of Host objects.
    :type  func: function
    :param func: The callback function.
    :type  only_authenticate: bool
    :param only_authenticate: don't authorize, just authenticate?
    :type  kwargs: dict
    :param kwargs: Passed to the Exscript.Queue constructor.
    """
    if only_authenticate:
        run(users, hosts, autoauthenticate()(func), **kwargs)
    else:
        run(users, hosts, autologin()(func), **kwargs)


def quickstart(hosts, func, only_authenticate=False, **kwargs):
    """
    Like quickrun(), but automatically logs into the host before passing
    the connection to the callback function.

    :type  hosts: Host|list[Host]
    :param hosts: A list of Host objects.
    :type  func: function
    :param func: The callback function.
    :type  only_authenticate: bool
    :param only_authenticate: don't authorize, just authenticate?
    :type  kwargs: dict
    :param kwargs: Passed to the Exscript.Queue constructor.
    """
    if only_authenticate:
        quickrun(hosts, autoauthenticate()(func), **kwargs)
    else:
        quickrun(hosts, autologin()(func), **kwargs)
