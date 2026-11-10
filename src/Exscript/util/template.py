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

All functions compile templates in secure mode by default: templates may not
call the functions of the standard library that run local commands or access
local files (``sys.exec``, ``sys.env``, and ``file.*`` except ``file.exists``).
Such calls raise :class:`Exscript.interpreter.exception.PermissionError` when
the template is compiled. Functions that the caller passes as variables are
allowed. Pass ``secure=False`` to allow all functions.
"""

from typing import TYPE_CHECKING, Any, cast

from Exscript import stdlib
from Exscript.interpreter import Parser
from Exscript.stdlib.util import secure_function

if TYPE_CHECKING:
    from Exscript.interpreter.program import Program
    from Exscript.protocols import Protocol

debug = 0


def _trusted(value: object) -> object:
    """
    Returns the given value of a template variable. A function that is not
    marked as secure is returned wrapped by secure_function(), so that a
    template that is compiled in secure mode may call it.
    """
    # Functions passed by the caller are allowed in secure mode.
    if callable(value) and not hasattr(value, '_is_secure'):
        return secure_function(value)
    return value


# Any: the variables of a template are lists whose items depend on the
# template, functions, or the connection; the parser options have
# different types.
def _compile(
    conn: 'Protocol | None',
    filename: str | None,
    template: str,
    parser_kwargs: dict[str, Any],
    **kwargs: Any,
) -> 'Program':
    """
    Compiles the given template with a new parser. The parser defines the
    built-in variables (``__filename__``, ``__username__``,
    ``__hostname__``, ``__response__`` and ``__connection__``), the
    functions of the standard library, and the given variables, which may
    override the built-in ones; the functions among them may be called in
    secure mode.

    :param conn: The connection on which the template runs, or None if the
        template is only compiled.
    :param filename: The name of the template file, or None.
    :param template: The template.
    :param parser_kwargs: The options of the parser; ``debug`` is added
        with the value of the debug variable of this module if it is
        missing.
    :param kwargs: Variables to define in the template.
    :return: The compiled template.
    """
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
    parser.define(**{name: _trusted(value) for name, value in kwargs.items()})

    # Compile the template. __filename__ is a list, as defined above or by
    # define(); the cast is for the type checker.
    return parser.parse(template, cast(list[str], parser.variables.get('__filename__'))[0])


def _run(
    conn: 'Protocol',
    filename: str | None,
    template: str,
    parser_kwargs: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Compiles the given template and runs it on the given connection, see
    _compile().

    :return: The variables that are defined after execution of the template.
    """
    compiled = _compile(conn, filename, template, parser_kwargs, **kwargs)
    return compiled.execute()


def test(string: str, secure: bool = True, **kwargs: Any) -> None:
    """
    Compiles the given template, and raises an exception if that
    failed. Does nothing otherwise.

    :type  string: string
    :param string: The template to compile.
    :type  secure: bool
    :param secure: Whether to forbid the insecure functions (see the module
        documentation).
    :type  kwargs: dict
    :param kwargs: Variables to define in the template.
    """
    parser_args = {'secure': secure, 'no_escaping': False}
    _compile(None, None, string, parser_args, **kwargs)


def test_file(filename: str, secure: bool = True, **kwargs: Any) -> None:
    """
    Convenience wrapper around test() that reads the template from a UTF-8
    file instead.

    :type  filename: string
    :param filename: The name of the template file.
    :type  secure: bool
    :param secure: Whether to forbid the insecure functions.
    :type  kwargs: dict
    :param kwargs: Variables to define in the template.
    """
    parser_args = {'secure': secure, 'no_escaping': False}
    with open(filename, encoding='utf-8') as fp:
        _compile(None, filename, fp.read(), parser_args, **kwargs)


def eval(
    conn: 'Protocol',
    string: str,
    strip_command: bool = True,
    no_escaping: bool = False,
    *,
    secure: bool = True,
    **kwargs: Any,
) -> dict[str, Any]:
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

    If strip_command is False, the response, (and hence, the ``filenames``
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
    :type  secure: bool
    :param secure: Whether to forbid the insecure functions (see the module
        documentation).
    :type  kwargs: dict
    :param kwargs: Variables to define in the template.
    :rtype:  dict
    :return: The variables that are defined after execution of the script.
    """
    parser_args = {'strip_command': strip_command, 'no_escaping': no_escaping, 'secure': secure}
    return _run(conn, None, string, parser_args, **kwargs)


def eval_file(
    conn: 'Protocol',
    filename: str,
    strip_command: bool = True,
    no_escaping: bool = False,
    *,
    secure: bool = True,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Convenience wrapper around eval() that reads the template from a UTF-8
    file instead.

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
    :type  secure: bool
    :param secure: Whether to forbid the insecure functions.
    :type  kwargs: dict
    :param kwargs: Variables to define in the template.
    :rtype:  dict
    :return: The variables that are defined after execution of the script.
    """
    parser_args = {'strip_command': strip_command, 'no_escaping': no_escaping, 'secure': secure}
    with open(filename, encoding='utf-8') as fp:
        return _run(conn, filename, fp.read(), parser_args, **kwargs)


def paste(
    conn: 'Protocol', string: str, no_escaping: bool = False, *, secure: bool = True, **kwargs: Any
) -> dict[str, Any]:
    """
    Compiles the given template and executes it on the given
    connection. This function differs from eval() such that it does not
    wait for a prompt after sending each command to the connected host.
    That means that the script can no longer read the response of the
    host, making commands such as ``extract`` or ``set_prompt`` useless.

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
    :type  secure: bool
    :param secure: Whether to forbid the insecure functions (see the module
        documentation).
    :type  kwargs: dict
    :param kwargs: Variables to define in the template.
    :rtype:  dict
    :return: The variables that are defined after execution of the script.
    """
    parser_args = {'no_prompt': True, 'no_escaping': no_escaping, 'secure': secure}
    return _run(conn, None, string, parser_args, **kwargs)


def paste_file(
    conn: 'Protocol',
    filename: str,
    no_escaping: bool = False,
    *,
    secure: bool = True,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Convenience wrapper around paste() that reads the template from a UTF-8
    file instead.

    :type  conn: Exscript.protocols.Protocol
    :param conn: The connection on which to run the template.
    :type  filename: string
    :param filename: The name of the template file.
    :type  no_escaping: bool
    :param no_escaping: Whether to disable advanced escape evaluation for
        control characters, octal, hexadecimal and unicode character sequences.
        Evaluation for CR, LF and TAB in strings is always enabled.
    :type  secure: bool
    :param secure: Whether to forbid the insecure functions.
    :type  kwargs: dict
    :param kwargs: Variables to define in the template.
    :rtype:  dict
    :return: The variables that are defined after execution of the script.
    """
    parser_args = {'no_prompt': True, 'no_escaping': no_escaping, 'secure': secure}
    with open(filename, encoding='utf-8') as fp:
        return _run(conn, filename, fp.read(), parser_args, **kwargs)
