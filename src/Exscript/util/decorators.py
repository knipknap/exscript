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
import Exscript
from Exscript             import stdlib
from Exscript.Interpreter import Parser
from Exscript.FooLib      import Interact

def os_function_mapper(conn, map, *data, **kwargs):
    os   = conn.guess_os()
    func = map.get(os)
    if func is None:
        raise Exception('No handler for %s found.' % os)
    return func(conn, *data, **kwargs)

def connect(function):
    def decorated(conn, *args, **kwargs):
        conn.open()
        function(conn, *args, **kwargs)
    return decorated

def autologin(function, wait = True):
    def decorated(conn, *args, **kwargs):
        conn.authenticate(wait = wait)
        function(conn, *args, **kwargs)
        conn.close(force = True)
    return connect(decorated)

def run_template(conn, template, **kwargs):
    # Define default variables.
    defaults = dict(__filename__ = template,
                    hostname     = conn.transport.get_host())

    # Init the parser and compile the template.
    parser = Parser()
    parser.define(**defaults)
    parser.define(**kwargs)
    parser.define_function(**stdlib.functions)
    compiled = parser.parse_file(template)
    compiled.define(**defaults)
    compiled.define(**kwargs)
    compiled.define(__connection__ = conn)

    # Run.
    return compiled.execute()
