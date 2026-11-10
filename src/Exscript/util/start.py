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

from collections.abc import Callable, Iterable
from typing import Any, cast

from .. import Account, Host, Queue
from .decorator import autoauthenticate, autologin
from .interact import read_login


def run(
    users: Account | Iterable[Account],
    hosts: str | Host | Iterable[str | Host],
    func: Callable[..., Any],
    **kwargs: Any,
) -> None:
    """
    Convenience function that creates an Exscript.Queue instance, adds
    the given accounts, and calls Queue.run() with the given
    hosts and function as an argument.

    The queue opens a connection to each host and calls the function as
    ``func(job, host, conn)``; the connection is not logged in yet.
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
    :type  hosts: str|Host|list(str|Host)
    :param hosts: A hostname or Host object, or a list of them.
    :type  func: function
    :param func: The callback function.
    :type  kwargs: dict
    :param kwargs: Passed to the Exscript.Queue constructor, except for
        ``attempts``, the number of attempts for each host (default 1),
        which is passed to Queue.run().
    """
    attempts = kwargs.get("attempts", 1)
    if "attempts" in kwargs:
        del kwargs["attempts"]
    # The queue is not annotated (it will be reworked); the cast is for the
    # type checker.
    queue = cast(Any, Queue)(**kwargs)
    queue.add_account(users)
    queue.run(hosts, func, attempts)
    queue.destroy()


def quickrun(
    hosts: str | Host | Iterable[str | Host], func: Callable[..., Any], **kwargs: Any
) -> None:
    """
    A wrapper around run() that creates the account by asking the user
    for entering his login information.

    :type  hosts: str|Host|list(str|Host)
    :param hosts: A hostname or Host object, or a list of them.
    :type  func: function
    :param func: The callback function.
    :type  kwargs: dict
    :param kwargs: Passed to run().
    """
    run(read_login(), hosts, func, **kwargs)


def start(
    users: Account | Iterable[Account],
    hosts: str | Host | Iterable[str | Host],
    func: Callable[..., Any],
    only_authenticate: bool = False,
    **kwargs: Any,
) -> None:
    """
    Like run(), but automatically logs into the host before passing
    the host to the callback function.

    :type  users: Account|list[Account]
    :param users: The account(s) to use for logging in.
    :type  hosts: str|Host|list(str|Host)
    :param hosts: A hostname or Host object, or a list of them.
    :type  func: function
    :param func: The callback function.
    :type  only_authenticate: bool
    :param only_authenticate: Whether to only authenticate, without
        authorizing (see :func:`Exscript.util.decorator.autoauthenticate`).
    :type  kwargs: dict
    :param kwargs: Passed to run().
    """
    if only_authenticate:
        run(users, hosts, autoauthenticate()(func), **kwargs)
    else:
        run(users, hosts, autologin()(func), **kwargs)


def quickstart(
    hosts: str | Host | Iterable[str | Host],
    func: Callable[..., Any],
    only_authenticate: bool = False,
    **kwargs: Any,
) -> None:
    """
    Like quickrun(), but automatically logs into the host before passing
    the connection to the callback function.

    :type  hosts: str|Host|list(str|Host)
    :param hosts: A hostname or Host object, or a list of them.
    :type  func: function
    :param func: The callback function.
    :type  only_authenticate: bool
    :param only_authenticate: Whether to only authenticate, without
        authorizing (see :func:`Exscript.util.decorator.autoauthenticate`).
    :type  kwargs: dict
    :param kwargs: Passed to run().
    """
    if only_authenticate:
        quickrun(hosts, autoauthenticate()(func), **kwargs)
    else:
        quickrun(hosts, autologin()(func), **kwargs)
