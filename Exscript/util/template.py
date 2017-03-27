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
Executing Exscript templates on a connection.
"""
from Exscript import stdlib
from Exscript.interpreter import Parser


def _compile(conn, filename, template, parser_kwargs, **kwargs):
    if conn:
        hostname = conn.get_host()
        account = conn.last_account
        username = account is not None and account.get_name() or None
    else:
        hostname = 'undefined'
        username = None

    # Init the parser.
    parser = Parser(**parser_kwargs)

    # Define the built-in variables and functions.
    builtin = dict(__filename__=[filename or 'undefined'],
                   __username__=[username],
                   __hostname__=[hostname],
                   __connection__=conn)
    parser.define_object(**builtin)
    parser.define_object(**stdlib.functions)

    # Allow for overriding built-in variables.
    parser.define(**kwargs)

    # Compile the template.
    return parser.parse(template, parser.variables.get('__filename__')[0])


def _run(conn, filename, template, parser_kwargs, **kwargs):
    compiled = _compile(conn, filename, template, parser_kwargs, **kwargs)
    return compiled.execute()


def test(string, **kwargs):
    """
    Compiles the given template, and raises an exception if that
    failed. Does nothing otherwise.

    :type  string: string
    :param string: The template to compile.
    :type  kwargs: dict
    :param kwargs: Variables to define in the template.
    """
    _compile(None, None, string, {}, **kwargs)


def test_secure(string, **kwargs):
    """
    Like test(), but makes sure that each function that is used in
    the template has the Exscript.stdlib.util.safe_function decorator.
    Raises Exscript.interpreter.Exception.PermissionError if any
    function lacks the decorator.

    :type  string: string
    :param string: The template to compile.
    :type  kwargs: dict
    :param kwargs: Variables to define in the template.
    """
    _compile(None, None, string, {'secure': True}, **kwargs)


def test_file(filename, **kwargs):
    """
    Convenience wrapper around test() that reads the template from a file
    instead.

    :type  filename: string
    :param filename: The name of the template file.
    :type  kwargs: dict
    :param kwargs: Variables to define in the template.
    """
    with open(filename) as fp:
        _compile(None, filename, fp.read(), {}, **kwargs)


def eval(conn, string, strip_command=True, **kwargs):
    """
    Compiles the given template and executes it on the given
    connection.
    Raises an exception if the compilation fails.

    if strip_command is True, the first line of each response that is
    received after any command sent by the template is stripped. For
    example, consider the following template::

        ls -1{extract /(\S+)/ as filenames}
        {loop filenames as filename}
            touch $filename
        {end}

    If strip_command is False, the response, (and hence, the `filenames'
    variable) contains the following::

        ls -1
        myfile
        myfile2
        [...]

    By setting strip_command to True, the first line is ommitted.

    :type  conn: Exscript.protocols.Protocol
    :param conn: The connection on which to run the template.
    :type  string: string
    :param string: The template to compile.
    :type  strip_command: bool
    :param strip_command: Whether to strip the command echo from the response.
    :type  kwargs: dict
    :param kwargs: Variables to define in the template.
    :rtype:  dict
    :return: The variables that are defined after execution of the script.
    """
    parser_args = {'strip_command': strip_command}
    return _run(conn, None, string, parser_args, **kwargs)


def eval_file(conn, filename, strip_command=True, **kwargs):
    """
    Convenience wrapper around eval() that reads the template from a file
    instead.

    :type  conn: Exscript.protocols.Protocol
    :param conn: The connection on which to run the template.
    :type  filename: string
    :param filename: The name of the template file.
    :type  strip_command: bool
    :param strip_command: Whether to strip the command echo from the response.
    :type  kwargs: dict
    :param kwargs: Variables to define in the template.
    """
    parser_args = {'strip_command': strip_command}
    with open(filename, 'r') as fp:
        return _run(conn, filename, fp.read(), parser_args, **kwargs)


def paste(conn, string, **kwargs):
    """
    Compiles the given template and executes it on the given
    connection. This function differs from eval() such that it does not
    wait for a prompt after sending each command to the connected host.
    That means that the script can no longer read the response of the
    host, making commands such as `extract' or `set_prompt' useless.

    The function raises an exception if the compilation fails, or if
    the template contains a command that requires a response from the
    host.

    :type  conn: Exscript.protocols.Protocol
    :param conn: The connection on which to run the template.
    :type  string: string
    :param string: The template to compile.
    :type  kwargs: dict
    :param kwargs: Variables to define in the template.
    :rtype:  dict
    :return: The variables that are defined after execution of the script.
    """
    return _run(conn, None, string, {'no_prompt': True}, **kwargs)


def paste_file(conn, filename, **kwargs):
    """
    Convenience wrapper around paste() that reads the template from a file
    instead.

    :type  conn: Exscript.protocols.Protocol
    :param conn: The connection on which to run the template.
    :type  filename: string
    :param filename: The name of the template file.
    :type  kwargs: dict
    :param kwargs: Variables to define in the template.
    """
    with open(filename, 'r') as fp:
        return _run(conn, None, fp.read(), {'no_prompt': True}, **kwargs)
