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
    def decorated(conn):
        return function(conn, *args, **kwargs)
    return decorated

def os_function_mapper(conn, map, *args, **kwargs):
    """
    When called with an open connection, this function uses the
    conn.guess_os() function to determine the operating system
    that is running on the connected host.
    It then uses the given map to look up a function name that corresponds
    to the operating system, and calls it. Example::

        def ios(conn):
            pass # Do something.

        def junos(conn):
            pass # Do something else.

        def shell(conn):
            pass # Do something else.

        Exscript.util.start.quickrun('myhost', os_function_mapper)

    An exception is raised if a matching function is not found in the map.

    @type  conn: Connection
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
    return func(conn, *args, **kwargs)

def connect(function):
    """
    Wraps the given function such that the connection is opened before
    calling it. Example::

        def my_func(conn):
            pass # Do something.
        Exscript.util.start.quickrun('myhost', connect(my_func))

    @type  function: function
    @param function: The function that's ought to be wrapped.
    @rtype:  function
    @return: The wrapped function.
    """
    def decorated(conn, *args, **kwargs):
        conn.open()
        result = function(conn, *args, **kwargs)
        conn.close(force = True)
        return result
    return decorated

def autologin(function, flush = True):
    """
    Wraps the given function such that...

        - the connection is opened, and
        - the user is logged in

    before calling calling it. Example::

        def my_func(conn):
            pass # Do something.
        Exscript.util.start.quickrun('myhost', autologin(my_func))

    @type  function: function
    @param function: The function that's ought to be wrapped.
    @type  flush: bool
    @param flush: Whether to flush the last prompt from the buffer.
    @rtype:  function
    @return: The wrapped function.
    """
    def decorated(conn, *args, **kwargs):
        conn.authenticate()
        conn.auto_authorize(flush = flush)
        result = function(conn, *args, **kwargs)
        conn.close(force = True)
        return result
    return connect(decorated)
