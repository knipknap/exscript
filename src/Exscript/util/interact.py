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
Tools for interacting with the user on the command line.
"""

import configparser
import getpass
import os
import sys
from collections.abc import Callable, Iterable

from .. import Account
from .cast import to_list


class InputHistory:
    """
    When prompting a user for input it is often useful to record his
    input in a file, and use previous input as a default value.
    This class allows for recording user input in a config file to
    allow for such functionality.
    """

    def __init__(
        self, filename: str = '~/.exscript_history', section: str = os.path.basename(sys.argv[0])
    ) -> None:
        """
        Constructor. The filename argument is the name of the config
        file; a leading ``~`` is expanded to the home directory.
        The optional section argument allows to specify
        a section under which the input is stored in the config file.
        The section defaults to the name of the running script.

        If the file can not be read, the history starts empty. Saving
        the input with set() raises OSError if the file can not be
        written.

        :type  filename: str
        :param filename: The config file.
        :type  section: str
        :param section: The section in the configfile.
        """
        self.section = section
        self.parser = configparser.ConfigParser()
        self.filename = os.path.expanduser(filename)

        self.parser.read(self.filename)
        if not self.parser.has_section(self.section):
            self.parser.add_section(self.section)

    def get[T](self, key: str, default: T | None = None) -> str | T | None:
        """
        Returns the input with the given key from the section that was
        passed to the constructor. If either the section or the key
        are not found, the default value is returned.

        :type  key: str
        :param key: The key for which to return a value.
        :type  default: str|object
        :param default: The default value that is returned.
        :rtype:  str|object
        :return: The value from the config file, or the default.
        """
        if not self.parser:
            return default
        try:
            return self.parser.get(self.section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return default

    def set(self, key: str, value: str | None) -> str | None:
        """
        Saves the input with the given key in the section that was
        passed to the constructor. If either the section or the key
        are not found, they are created.

        Does nothing if the given value is None.

        :type  key: str
        :param key: The key for which to define a value.
        :type  value: str|None
        :param value: The value that is defined, or None.
        :rtype:  str|None
        :return: The given value.
        """
        if value is None:
            return None

        self.parser.set(self.section, key, value)
        with open(self.filename, encoding='utf-8', mode="w") as fp:
            self.parser.write(fp)
        return value


def prompt(
    key: str,
    message: str,
    default: str | None = None,
    doverh: bool = True,
    strip: bool = True,
    check: Callable[[str], str | Iterable[str] | None] | None = None,
    history: InputHistory | None = None,
) -> str:
    """
    Prompts the user for input. This function is similar to Python's built
    in input(), with the following differences:

        - You may specify a default value that is returned if the user
          presses "enter" without entering anything.
        - The user's input is recorded in a config file, and offered
          as the default value the next time this function is used
          (based on the key argument).

    The config file is based around the :class:`InputHistory`. If a history object
    is not passed in the history argument, a new one will be created.

    The key argument specifies under which name the input is saved in the
    config file.

    If no default value is given, or if doverh is False, the value from the
    history is offered as the default; the given default value is only used
    if the history has no value.

    The strip argument specifies that the returned value should be stripped
    of whitespace (default).

    The check argument allows for validating the input; if the validation
    fails, the user is prompted again before the value is stored in the
    InputHistory. Example usage::

        def validate(input):
            if len(input) < 4:
                return 'Please enter at least 4 characters!'
        value = prompt('test', 'Enter a value', 'My Default', doverh=False, check=validate)
        print('You entered:', value)

    This leads to the following output::

        Enter a value [My Default]: abc
        Please enter at least 4 characters!
        Enter a value [My Default]: Foobar
        You entered: Foobar

    The next time the same code is started, the input 'Foobar' is remembered::

        Enter a value [Foobar]:        (enters nothing)
        You entered: Foobar

    :type  key: str
    :param key: The key under which to store the input in the :class:`InputHistory`.
    :type  message: str
    :param message: The user prompt.
    :type  default: str|None
    :param default: The offered default value, see above.
    :type  doverh: bool
    :param doverh: Whether to prefer default value over history value.
    :type  strip: bool
    :param strip: Whether to remove whitespace from the input.
    :type  check: callable
    :param check: A function that is called for validating the input. It
        returns None if the input is valid, and an error message or a list
        of error messages otherwise.
    :type  history: :class:`InputHistory` or None
    :param history: The history used for recording default values, or None.
    :return: The input, or the default value if the user entered nothing.
    """
    if history is None:
        history = InputHistory()
    if not doverh or default is None:
        default = history.get(key, str(default))
    while True:
        if default is None:
            value = input('%s: ' % message)
        else:
            value = input('%s [%s]: ' % (message, default)) or default
        if strip and isinstance(value, str):
            value = value.strip()
        if not check:
            break
        errors = check(value)
        if errors:
            print('\n'.join(to_list(errors)))
        else:
            break
    history.set(key, value)
    return value


def get_filename(
    key: str, message: str, default: str | None = None, history: InputHistory | None = None
) -> str:
    """
    Like :meth:`prompt`, but only accepts the name of an existing file
    as an input.

    :type  key: str
    :param key: The key under which to store the input in the :class:`InputHistory`.
    :type  message: str
    :param message: The user prompt.
    :type  default: str|None
    :param default: The offered default value, see :meth:`prompt`.
    :type  history: :class:`InputHistory` or None
    :param history: The history used for recording default values, or None.
    :return: The name of the file.
    """

    def _validate(string: str) -> str | None:
        if not os.path.isfile(string):
            return 'File not found. Please enter a filename.'
        return None

    return prompt(key, message, default, check=_validate, history=history)


def get_user(prompt: str | None = None) -> str:
    """
    Prompts the user for his login name, defaulting to the USER environment
    variable. Returns a string containing the username.
    May throw an exception if EOF is given by the user.

    :type  prompt: str|None
    :param prompt: The user prompt or the default one if None.
    :rtype:  string
    :return: A username.
    """
    # Read username and password.
    try:
        env_user = getpass.getuser()
    except KeyError:
        env_user = ''
    if prompt is None:
        prompt = "Please enter your user name"
    if env_user is None or env_user == '':
        user = input('%s: ' % prompt)
    else:
        user = input('%s [%s]: ' % (prompt, env_user))
        if user == '':
            user = env_user
    return user


def get_login() -> tuple[str, str]:
    """
    Prompts the user for the login name using get_user(), and also asks for
    the password.
    Returns a tuple containing the username and the password.
    May throw an exception if EOF is given by the user.

    :rtype:  (string, string)
    :return: A tuple containing the username and the password.
    """
    user = get_user()
    password = getpass.getpass('Please enter your password: ')
    return user, password


def read_login() -> Account:
    """
    Like get_login(), but returns an Account object.

    :rtype:  Account
    :return: A new account.
    """
    user, password = get_login()
    return Account(user, password)
