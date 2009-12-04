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
from Exscript             import stdlib
from Exscript.Interpreter import Parser

def _builtin_vars(conn = None, filename = 'undefined'):
    hostname = conn and conn.get_host().get_address() or 'undefined'
    builtin  = dict(__filename__   = [filename],
                    __hostname__   = [hostname],
                    __connection__ = conn)
    return builtin

def _compile(template, parser_kwargs, **kwargs):
    # Init the parser and compile the template.
    parser = Parser(**parser_kwargs)
    parser.define_object(**kwargs)
    parser.define_object(**stdlib.functions)
    return parser.parse(template)

def _run(conn, template, parser_kwargs, **kwargs):
    compiled = _compile(template, parser_kwargs, **kwargs)
    return compiled.execute()

def test(template, **kwargs):
    kwargs.update(_builtin_vars())
    return _compile(template, {}, **kwargs)

def eval(conn, string, strip_command = True, **kwargs):
    kwargs.update(_builtin_vars(conn))
    return _run(conn, string, {'strip_command': strip_command}, **kwargs)

def paste(conn, string, **kwargs):
    kwargs.update(_builtin_vars(conn))
    return _run(conn, string, {'no_prompt': True}, **kwargs)

def eval_file(conn, filename, strip_command = True, **kwargs):
    kwargs.update(_builtin_vars(conn, filename))
    template = open(filename, 'r').read()
    return _run(conn, template, {'strip_command': strip_command}, **kwargs)

def paste_file(conn, filename, **kwargs):
    kwargs.update(_builtin_vars(conn, filename))
    template = open(filename, 'r').read()
    return _run(conn, template, {'no_prompt': True}, **kwargs)
