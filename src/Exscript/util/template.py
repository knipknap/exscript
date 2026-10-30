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

debug = 0


def _compile(conn, filename, template, parser_kwargs, **kwargs):
    undefined = 'undefined'
    if conn:
        hostname = conn.get_host()
        account = conn._last_account
        username = account is not None and account.get_name() or undefined
    else:
        hostname = undefined
        username = undefined

    # Init the parser.
    if "debug" not in parser_kwargs:
        parser_kwargs["debug"] = debug
    parser = Parser(**parser_kwargs)

    # Define the built-in variables and functions.
    builtin = dict(
        __filename__=[filename or undefined],
        __username__=[username],
        __hostname__=[hostname],
        __response__=[''],
        __connection__=conn,
    )
    parser.define_object(**builtin)
    parser.define_object(**stdlib.functions)

    # Allow for overriding built-in variables.
    parser.define(**kwargs)

    # Compile the template.
    return parser.parse(template, parser.variables.get('__filename__')[0])


def _run(conn, filename, template, parser_kwargs, **kwargs):
    compiled = _compile(conn, filename, template, parser_kwargs, **kwargs)
    return compiled.execute()


def test(string, secure=False, **kwargs):
    """
    Compiles the given template, and raises an exception if that
    failed. Does nothing otherwise.

    With secure mode enabled it makes sure that each function that is used in
    the template has the Exscript.stdlib.util.safe_function decorator.
    Raises Exscript.interpreter.Exception.PermissionError if any function
    lacks the decorator.

    :type  string: string
    :param string: The template to compile.
    :type  secure: bool
    :param secure: Whether to enable secure mode.
    :type  kwargs: dict
    :param kwargs: Variables to define in the template.
    """
    parser_args = {'secure': secure, 'no_escaping': False}
    _compile(None, None, string, parser_args, **kwargs)


def test_file(filename, secure=False, **kwargs):
    """
    Convenience wrapper around test() that reads the template from a file
    instead.

    :type  filename: string
    :param filename: The name of the template file.
    :type  kwargs: dict
    :param kwargs: Variables to define in the template.
    """
    parser_args = {'secure': secure, 'no_escaping': False}
    with open(filename) as fp:
        _compile(None, filename, fp.read(), parser_args, **kwargs)


def eval(conn, string, strip_command=True, no_escaping=False, **kwargs):
    r"""
    Compiles the given template and executes it on the given connection.
    Raises an exception if the compilation fails.

    If strip_command is True, the first line of each response that is
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

    By setting strip_command to True, the first line is omitted.

    :type  conn: Exscript.protocols.Protocol
    :param conn: The connection on which to run the template.
    :type  string: string
    :param string: The template to compile.
    :type  strip_command: bool
    :param strip_command: Whether to strip the command echo from the response.
    :type  no_escaping: bool
    :param no_escaping: Whether to disable advanced escape evaluation for
        control characters, octal, hexadecimal and unicode character sequences.
        Evaluation for CR, LF and TAB in strings is always enabled.
    :type  kwargs: dict
    :param kwargs: Variables to define in the template.
    :rtype:  dict
    :return: The variables that are defined after execution of the script.
    """
    parser_args = {'strip_command': strip_command, 'no_escaping': no_escaping}
    return _run(conn, None, string, parser_args, **kwargs)


def eval_file(conn, filename, strip_command=True, no_escaping=False, **kwargs):
    """
    Convenience wrapper around eval() that reads the template from a file
    instead.

    :type  conn: Exscript.protocols.Protocol
    :param conn: The connection on which to run the template.
    :type  filename: string
    :param filename: The name of the template file.
    :type  strip_command: bool
    :param strip_command: Whether to strip the command echo from the response.
    :type  no_escaping: bool
    :param no_escaping: Whether to disable advanced escape evaluation for
        control characters, octal, hexadecimal and unicode character sequences.
        Evaluation for CR, LF and TAB in strings is always enabled.
    :type  kwargs: dict
    :param kwargs: Variables to define in the template.
    """
    parser_args = {'strip_command': strip_command, 'no_escaping': no_escaping}
    with open(filename, 'r') as fp:
        return _run(conn, filename, fp.read(), parser_args, **kwargs)


def paste(conn, string, no_escaping=False, **kwargs):
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
    :type  no_escaping: bool
    :param no_escaping: Whether to disable advanced escape evaluation for
        control characters, octal, hexadecimal and unicode character sequences.
        Evaluation for CR, LF and TAB in strings is always enabled.
    :type  kwargs: dict
    :param kwargs: Variables to define in the template.
    :rtype:  dict
    :return: The variables that are defined after execution of the script.
    """
    parser_args = {'no_prompt': True, 'no_escaping': no_escaping}
    return _run(conn, None, string, parser_args, **kwargs)


def paste_file(conn, filename, no_escaping=False,  **kwargs):
    """
    Convenience wrapper around paste() that reads the template from a file
    instead.

    :type  conn: Exscript.protocols.Protocol
    :param conn: The connection on which to run the template.
    :type  filename: string
    :param filename: The name of the template file.
    :type  no_escaping: bool
    :param no_escaping: Whether to disable advanced escape evaluation for
        control characters, octal, hexadecimal and unicode character sequences.
        Evaluation for CR, LF and TAB in strings is always enabled.
    :type  kwargs: dict
    :param kwargs: Variables to define in the template.
    """
    parser_args = {'no_prompt': True, 'no_escaping': no_escaping}
    with open(filename, 'r') as fp:
        return _run(conn, filename, fp.read(), parser_args, **kwargs)
