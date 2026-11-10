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
The functions of the template language that use the connection, such as
``connection.exec()`` or ``connection.set_prompt()``.
"""

import re
from typing import TYPE_CHECKING

from ..account import Account
from .util import secure_function

if TYPE_CHECKING:
    from ..interpreter.scope import Scope
    from ..protocols import Protocol


@secure_function
def authenticate(scope: 'Scope') -> bool:
    """
    Looks for any username/password prompts on the current connection
    and logs in using the login information that was passed to Exscript.
    """
    scope.get('__connection__').app_authenticate()
    return True


@secure_function
def authenticate_user(
    scope: 'Scope', user: list[str | None] = [None], password: list[str | None] = [None]
) -> bool:
    """
    Like authenticate(), but logs in using the given user and password.
    If a user and password are not given, the function uses the same
    user and password that were used at the last login attempt; it is
    an error if no such attempt was made before.

    :type  user: string
    :param user: A username.
    :type  password: string
    :param password: A password.
    """
    conn: Protocol = scope.get('__connection__')
    username = user[0]
    if username is None:
        conn.app_authenticate()
    else:
        account = Account(username, password[0])
        conn.app_authenticate(account)
    return True


@secure_function
def authorize(scope: 'Scope', password: list[str | None] = [None]) -> bool:
    """
    Looks for a password prompt on the current connection
    and enters the given password.
    If a password is not given, the function uses the same
    password that was used at the last login attempt; it is
    an error if no such attempt was made before.

    :type  password: string
    :param password: A password.
    """
    conn: Protocol = scope.get('__connection__')
    secret = password[0]
    if secret is None:
        conn.app_authorize()
    else:
        account = Account('', secret)
        conn.app_authorize(account)
    return True


@secure_function
def auto_authorize(scope: 'Scope', password: list[str | None] = [None]) -> bool:
    """
    Executes a command on the remote host that causes an authorization
    procedure to be started, then authorizes using the given password
    in the same way in which authorize() works.
    The command depends on the driver of the connection; on IOS, for
    example, it is "enable". Drivers that have no such command only
    authorize, like authorize().

    :type  password: string
    :param password: A password.
    """
    conn: Protocol = scope.get('__connection__')
    secret = password[0]
    if secret is None:
        conn.auto_app_authorize()
    else:
        account = Account('', secret)
        conn.auto_app_authorize(account)
    return True


@secure_function
def autoinit(scope: 'Scope') -> bool:
    """
    Makes the remote host more script-friendly by automatically executing
    one or more commands on it.
    The commands executed depend on the currently used driver.
    For example, the driver for Cisco IOS would execute the
    following commands::

        term len 0
        term width 0
    """
    scope.get('__connection__').autoinit()
    return True


@secure_function
def close(scope: 'Scope', force: list[bool] = [False]) -> bool:
    """
    Closes the existing connection with the remote host gracefully, sending
    the driver-specific logout command first. This function is rarely used
    from templates, as normally Exscript closes the connection automatically
    when the script has completed.

    :type  force: boolean
    :param force: Whether the connection is closed without logout.
    """
    conn: Protocol = scope.get('__connection__')
    conn.close(force=force[0])
    scope.define(__response__=conn.get_response().split('\n'))
    return True


@secure_function
def exec_(scope: 'Scope', data: list[str]) -> bool:
    """
    Sends the given data to the remote host and waits until the host
    has responded with a prompt.
    If the given data is a list of strings, each item is sent, and
    after each item a prompt is expected.

    This function also causes the response of the command to be stored
    in the built-in __response__ variable.

    :type  data: string
    :param data: The data that is sent.
    """
    conn: Protocol = scope.get('__connection__')
    response = []
    for line in data:
        conn.send(line)
        conn.expect_prompt()
        response += conn.get_response().split('\n')
    scope.define(__response__=response)
    return True


@secure_function
def execline(scope: 'Scope', data: list[str]) -> bool:
    """
    Like exec(), but appends a newline to the data before sending it.

    :type  data: string
    :param data: The data that is sent.
    """
    conn: Protocol = scope.get('__connection__')
    response = []
    for line in data:
        conn.send(line + '\r')
        conn.expect_prompt()
        response += conn.get_response().split('\n')
    scope.define(__response__=response)
    return True


@secure_function
def get_protocol(scope: 'Scope') -> list[str]:
    """
    Returns the name of the connection protocol.

    This is the class name of the protocol adapter in lower-case without
    any trailing digits.

    :rtype:  string
    :return: The connection protocol.
    """
    conn: Protocol = scope.get('__connection__')
    return [conn.get_protocol()]


@secure_function
def guess_os(scope: 'Scope') -> list[str]:
    """
    Guesses the operating system of the connected host.

    The recognition is based on the past conversation that has happened
    on the host; Exscript looks for known patterns and maps them to specific
    operating systems.

    :rtype:  string
    :return: The operating system.
    """
    conn: Protocol = scope.get('__connection__')
    return [conn.guess_os()]


@secure_function
def send(scope: 'Scope', data: list[str]) -> bool:
    """
    Like exec(), but does not wait for a response of the remote host after
    sending the data.

    :type  data: string
    :param data: The data that is sent.
    """
    conn: Protocol = scope.get('__connection__')
    for line in data:
        conn.send(line)
    scope.define(__response__=conn.get_response().split('\n'))
    return True


@secure_function
def sendline(scope: 'Scope', data: list[str]) -> bool:
    """
    Like execline(), but does not wait for a response of the remote host after
    sending the data.

    :type  data: string
    :param data: The data that is sent.
    """
    conn: Protocol = scope.get('__connection__')
    for line in data:
        conn.send(line + '\r')
    scope.define(__response__=conn.get_response().split('\n'))
    return True


@secure_function
def expect(scope: 'Scope', prompt: re.Pattern[str] | list[str | re.Pattern[str]]) -> bool:
    """
    Waits until the response of the remote host contains the given pattern.

    Does consume the prompt, can be run only once, then it fails with a timeout.

    :type  prompt: regex
    :param prompt: The prompt pattern.
    """
    conn: Protocol = scope.get('__connection__')
    conn.expect(prompt)
    scope.define(__response__=conn.get_response().split('\n'))
    return True


@secure_function
def wait_for(scope: 'Scope', prompt: re.Pattern[str] | list[str | re.Pattern[str]]) -> bool:
    """
    Waits until the response of the remote host contains the given pattern.

    Does not consume the prompt, can be rerun multiple times.

    :type  prompt: regex
    :param prompt: The prompt pattern.
    """
    conn: Protocol = scope.get('__connection__')
    conn.waitfor(prompt)
    scope.define(__response__=conn.get_response().split('\n'))
    return True


@secure_function
def set_prompt(
    scope: 'Scope', prompt: re.Pattern[str] | list[str | re.Pattern[str]] | None = None
) -> bool:
    """
    Defines the pattern that is recognized at any future time when Exscript
    needs to wait for a prompt.
    In other words, whenever Exscript waits for a prompt, it searches the
    response of the host for the given pattern and continues as soon as the
    pattern is found.

    Exscript waits for a prompt whenever it sends a command (unless the send()
    method was used). set_prompt() redefines as to what is recognized as a
    prompt. Without a pattern, the default pattern of the driver is used
    again.

    :type  prompt: regex
    :param prompt: The prompt pattern.
    """
    conn: Protocol = scope.get('__connection__')
    conn.set_prompt(prompt, extend=False)
    return True


@secure_function
def add_prompt(scope: 'Scope', prompt: re.Pattern[str] | list[str | re.Pattern[str]]) -> bool:
    """
    Extends the current list of patterns, that are recognized at any future time
    when Exscript needs to wait for a prompt, each time when called. Use
    set_prompt() instead to replace the current/default pattern.

    :type  prompt: regex
    :param prompt: The additional prompt pattern.
    """
    conn: Protocol = scope.get('__connection__')
    conn.set_prompt(prompt, extend=True)
    return True


@secure_function
def set_error(
    scope: 'Scope', error_re: re.Pattern[str] | list[str | re.Pattern[str]] | None = None
) -> bool:
    """
    Defines a pattern that, whenever detected in the response of the remote
    host, causes an error to be raised.

    In other words, whenever Exscript waits for a prompt, it searches the
    response of the host for the given pattern and raises an error if the
    pattern is found. Without a pattern, the default pattern of the driver
    is used again.

    :type  error_re: regex
    :param error_re: The error pattern.
    """
    conn: Protocol = scope.get('__connection__')
    conn.set_error_prompt(error_re, extend=False)
    return True


@secure_function
def add_error(scope: 'Scope', error_re: re.Pattern[str] | list[str | re.Pattern[str]]) -> bool:
    """
    Extends the list of patterns, that, whenever detected in the response of the
    remote host, cause an error to be raised. Use set_error() instead to replace
    the current/default pattern.

    :type  error_re: regex
    :param error_re: The additional error pattern.
    """
    conn: Protocol = scope.get('__connection__')
    conn.set_error_prompt(error_re, extend=True)
    return True


@secure_function
def set_timeout(scope: 'Scope', timeout: list[int | str]) -> bool:
    """
    Defines the time after which Exscript fails if it does not receive a
    prompt from the remote host.

    :type  timeout: int
    :param timeout: The timeout in seconds.
    """
    conn: Protocol = scope.get('__connection__')
    conn.set_timeout(int(timeout[0]))
    return True
