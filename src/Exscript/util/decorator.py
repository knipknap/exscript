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
Decorators for callbacks passed to Queue.run().
"""
from functools import partial
from Exscript.AccountProxy import AccountProxy
from Exscript.protocols import get_protocol_from_name
from Exscript.protocols.Exception import LoginFailure

def bind(function, *args, **kwargs):
    """
    Wraps the given function such that when it is called, the given arguments
    are passed in addition to the connection argument.

    @type  function: function
    @param function: The function that's ought to be wrapped.
    @type  args: list
    @param args: Passed on to the called function.
    @type  kwargs: dict
    @param kwargs: Passed on to the called function.
    @rtype:  function
    @return: The wrapped function.
    """
    def decorated(*inner_args, **inner_kwargs):
        kwargs.update(inner_kwargs)
        return function(*(inner_args + args), **kwargs)
    return decorated

def os_function_mapper(job, host, conn, map, *args, **kwargs):
    """
    When called with an open connection, this function uses the
    conn.guess_os() function to determine the operating system
    that is running on the connected host.
    It then uses the given map to look up a function name that corresponds
    to the operating system, and calls it. Example::

        def ios_xr(job, host, conn):
            pass # Do something.

        def junos(job, host, conn):
            pass # Do something else.

        def shell(job, host, conn):
            pass # Do something else.

        Exscript.util.start.quickrun('myhost', os_function_mapper)

    An exception is raised if a matching function is not found in the map.

    @type  conn: Exscript.protocols.Protocol
    @param conn: The open connection.
    @type  map: dict
    @param map: A dictionary mapping operating system name to a function.
    @type  args: list
    @param args: Passed on to the called function.
    @type  kwargs: dict
    @param kwargs: Passed on to the called function.
    @rtype:  object
    @return: The return value of the called function.
    """
    os   = conn.guess_os()
    func = map.get(os)
    if func is None:
        raise Exception('No handler for %s found.' % os)
    return func(job, host, conn, *args, **kwargs)

def _account_factory(accm, host, account):
    if account is None:
        account = host.get_account()

    # Specific account requested?
    if account:
        account = AccountProxy.for_account_hash(accm, account.__hash__())
    else:
        account = AccountProxy.for_host(accm, host)

    return account

def connect(protocol_args = None):
    """
    Wraps the given function such that the connection is opened before
    calling it. Example::

        @connect(protocol_args = {'debug': 1})
        def my_func(job, host, conn):
            pass # Do something.
        Exscript.util.start.quickrun('myhost', my_func)

    @type  protocol_args: dict
    @param protocol_args: Passed to the Exscript.protocol.Protocol constructor.
    @rtype:  function
    @return: The wrapped function.
    """
    if protocol_args is None:
        protocol_args = {}

    def decorator(function):
        def decorated(job, host, *args, **kwargs):
            # Define the protocol options that were attached to the
            # job by the queue.
            pipe, stdout = job.data
            mkaccount = partial(_account_factory, pipe, host)
            pargs     = protocol_args.copy()
            pargs.setdefault('account_factory', mkaccount)
            pargs.setdefault('stdout', stdout)

            # Create a protocol adapter.
            protocol_name = host.get_protocol()
            protocol_cls  = get_protocol_from_name(protocol_name)
            protocol      = protocol_cls(**pargs)

            # Special case: Define the behaviour of the pseudo protocol
            # adapter.
            if protocol_name == 'pseudo':
                filename = host.get_address()
                protocol.device.add_commands_from_file(filename)

            # Open the connection.
            protocol.connect(host.get_address(), host.get_tcp_port())
            result = function(job, host, protocol, *args, **kwargs)
            protocol.close(force = True)
            return result
        return decorated
    return decorator

def autologin(flush = True, attempts = 1):
    """
    Wraps the given function such that conn.login() is executed
    before calling it. Example::

        @connect(debug = 1)
        @autologin(attempts = 2)
        def my_func(job, host, conn):
            pass # Do something.
        Exscript.util.start.quickrun('myhost', my_func)

    @type  flush: bool
    @param flush: Whether to flush the last prompt from the buffer.
    @type  attempts: int
    @param attempts: The number of login attempts if login fails.
    @rtype:  function
    @return: The wrapped function.
    """
    def decorator(function):
        def decorated(job, host, conn, *args, **kwargs):
            failed = 0
            while True:
                try:
                    conn.login(flush = flush)
                except LoginFailure, e:
                    failed += 1
                    if failed >= attempts:
                        raise
                    continue
                break
            return function(job, host, conn, *args, **kwargs)
        return decorated
    return decorator
