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
Decorators for callbacks passed to Queue.run().
"""
from __future__ import absolute_import
from .impl import add_label, get_label, copy_labels
from ..protocols.exception import LoginFailure


def bind(function, *args, **kwargs):
    """
    Wraps the given function such that when it is called, the given arguments
    are passed in addition to the connection argument.

    :type  function: function
    :param function: The function that's ought to be wrapped.
    :type  args: list
    :param args: Passed on to the called function.
    :type  kwargs: dict
    :param kwargs: Passed on to the called function.
    :rtype:  function
    :return: The wrapped function.
    """
    def decorated(*inner_args, **inner_kwargs):
        kwargs.update(inner_kwargs)
        return function(*(inner_args + args), **kwargs)
    copy_labels(function, decorated)
    return decorated


def os_function_mapper(map):
    """
    When called with an open connection, this function uses the
    conn.guess_os() function to guess the operating system
    of the connected host.
    It then uses the given map to look up a function name that corresponds
    to the operating system, and calls it. Example::

        def ios_xr(job, host, conn):
            pass # Do something.

        def junos(job, host, conn):
            pass # Do something else.

        def shell(job, host, conn):
            pass # Do something else.

        Exscript.util.start.quickrun('myhost', os_function_mapper(globals()))

    An exception is raised if a matching function is not found in the map.

    :type  conn: Exscript.protocols.Protocol
    :param conn: The open connection.
    :type  map: dict
    :param map: A dictionary mapping operating system name to a function.
    :type  args: list
    :param args: Passed on to the called function.
    :type  kwargs: dict
    :param kwargs: Passed on to the called function.
    :rtype:  object
    :return: The return value of the called function.
    """
    def decorated(job, host, conn, *args, **kwargs):
        os = conn.guess_os()
        func = map.get(os)
        if func is None:
            raise Exception('No handler for %s found.' % os)
        return func(job, host, conn, *args, **kwargs)
    return decorated


def _decorate(flush=True, attempts=1, only_authenticate=False):
    """
    Wraps the given function such that conn.login() or conn.authenticate() is
    executed.
    Doing the real work for autologin and autoauthenticate to minimize code
    duplication.

    :type  flush: bool
    :param flush: Whether to flush the last prompt from the buffer.
    :type  attempts: int
    :param attempts: The number of login attempts if login fails.
    :type only_authenticate: bool
    :param only_authenticate: login or only authenticate (don't authorize)?
    :rtype:  function
    :return: The wrapped function.
    """
    def decorator(function):
        def decorated(job, host, conn, *args, **kwargs):
            failed = 0
            while True:
                try:
                    if only_authenticate:
                        conn.authenticate(flush=flush)
                    else:
                        conn.login(flush=flush)
                except LoginFailure as e:
                    failed += 1
                    if failed >= attempts:
                        raise
                    continue
                break
            return function(job, host, conn, *args, **kwargs)
        copy_labels(function, decorated)
        return decorated
    return decorator


def autologin(flush=True, attempts=1):
    """
    Wraps the given function such that conn.login() is executed
    before calling it. Example::

        @autologin(attempts = 2)
        def my_func(job, host, conn):
            pass # Do something.
        Exscript.util.start.quickrun('myhost', my_func)

    :type  flush: bool
    :param flush: Whether to flush the last prompt from the buffer.
    :type  attempts: int
    :param attempts: The number of login attempts if login fails.
    :rtype:  function
    :return: The wrapped function.
    """
    return _decorate(flush, attempts)


def autoauthenticate(flush=True, attempts=1):
    """
    Wraps the given function such that conn.authenticate() is executed
    before calling it. Example::

        @autoauthenticate(attempts = 2)
        def my_func(job, host, conn):
            pass # Do something.
        Exscript.util.start.quickrun('myhost', my_func)

    :type  flush: bool
    :param flush: Whether to flush the last prompt from the buffer.
    :type  attempts: int
    :param attempts: The number of login attempts if login fails.
    :rtype:  function
    :return: The wrapped function.
    """
    return _decorate(flush, attempts, only_authenticate=True)
