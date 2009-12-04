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
import re, os, base64
from Exscript             import stdlib
from Exscript.Interpreter import Parser
from Exscript.FooLib      import Interact

def os_function_mapper(conn, map, *args, **kwargs):
    """
    When called with an open connection, this function uses the
    conn.guess_os() function to determine the operating system
    that is running on the connected host.
    It then uses the given map to look up a function name that corresponds
    to the operating system, and calls it. Example:

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
    calling it. Example:

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
        function(conn, *args, **kwargs)
    return decorated

def autologin(function, wait = True):
    """
    Wraps the given function such that

        - the connection is opened, and
        - the user is logged in

    before calling calling it. Example:

        def my_func(conn):
            pass # Do something.
        Exscript.util.start.quickrun('myhost', autologin(my_func))

    @type  function: function
    @param function: The function that's ought to be wrapped.
    @type  wait: bool
    @param wait: Whether to wait for a prompt after logging in.
    @rtype:  function
    @return: The wrapped function.
    """
    def decorated(conn, *args, **kwargs):
        conn.authenticate(wait = wait)
        function(conn, *args, **kwargs)
        conn.close(force = True)
    return connect(decorated)

def _builtin_vars(conn = None, filename = 'undefined'):
    hostname = conn and conn.get_host().get_address() or 'undefined'
    builtin  = dict(__filename__   = [filename],
                    __hostname__   = [hostname],
                    __connection__ = conn)
    return builtin

def _compile_template(template, parser_kwargs, **kwargs):
    # Init the parser and compile the template.
    parser = Parser(**parser_kwargs)
    parser.define_object(**kwargs)
    parser.define_object(**stdlib.functions)
    return parser.parse(template)

def test_template(template, **kwargs):
    kwargs.update(_builtin_vars())
    return _compile_template(template, {}, **kwargs)

def _run_tmpl(conn, template, parser_kwargs, **kwargs):
    compiled = _compile_template(template, parser_kwargs, **kwargs)
    return compiled.execute()

def run_template_string(conn, string, strip_command = True, **kwargs):
    kwargs.update(_builtin_vars(conn))
    return _run_tmpl(conn, string, {'strip_command': strip_command}, **kwargs)

def paste_template_string(conn, string, **kwargs):
    kwargs.update(_builtin_vars(conn))
    return _run_tmpl(conn, string, {'no_prompt': True}, **kwargs)

def run_template(conn, filename, strip_command = True, **kwargs):
    kwargs.update(_builtin_vars(conn, filename))
    template = open(filename, 'r').read()
    return _run_tmpl(conn, template, {'strip_command': strip_command}, **kwargs)

def paste_template(conn, filename, **kwargs):
    kwargs.update(_builtin_vars(conn, filename))
    template = open(filename, 'r').read()
    return _run_tmpl(conn, template, {'no_prompt': True}, **kwargs)
