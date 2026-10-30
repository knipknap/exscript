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
Defines the behavior of commands by mapping commands to functions.
"""

import re
from collections.abc import Iterable


class CommandSet:
    """
    A set of commands to be used by the Dummy adapter.
    """

    def __init__(self, strict=True):
        """
        Constructor.
        """
        self.strict = strict
        self.response_list = []

    def __deepcopy__(self, memo):
        cmdset = CommandSet(self.strict)
        for regex, response in self.response_list:
            regex = re.compile(regex.pattern, regex.flags)
            cmdset.response_list.append((regex, response))
        return cmdset

    def add(self, command, handler, handler_decorator=None):
        """
        Register a command and response handler pair.

        The command may be either a string (which is then automatically
        compiled into a regular expression), or a pre-compiled regular
        expression object.

        If the given response handler is a string, it is sent as the
        response to any command that matches the given regular expression.
        If the given response handler is a function, it is called
        with the command passed as an argument.

        :type  command: str|regex
        :param command: A string or a compiled regular expression.
        :type  handler: function|str
        :param handler: A response, or a response handler.
        :type  handler_decorator: function
        :param handler_decorator: A function that is used to decorate
               the response or response handler.
        """
        command = re.compile(command)
        if handler_decorator:
            handler = handler_decorator(handler)
        self.response_list.append((command, handler))

    def add_from_file(self, filename, handler_decorator=None):
        """
        Wrapper around add() that reads the response handlers from the
        file with the given name. The file is a Python script containing
        a list named 'commands' of tuples that map command names to
        response handlers.

        :type  filename: str
        :param filename: The name of the file containing the tuples.
        :type  handler_decorator: function
        :param handler_decorator: A function that is used to decorate
               each of the responses or response handlers in the file.
        :raises ValueError: Raised when the file does not define a variable
            named "commands" or if "commands" is not iterable.
        """
        args = {}
        with open(filename, encoding="utf-8") as fin:
            source = fin.read()
        code = compile(source, filename, mode="exec")
        exec(code, args)  # noqa: S102

        commands = args.get('commands')
        if commands is None:
            raise ValueError(filename + ': no variable named "commands"')
        elif not isinstance(commands, Iterable):
            raise ValueError(filename + ': variable "commands" is not iterable')
        for command, response in commands:
            self.add(command, response, handler_decorator)

    def eval(self, command):
        """
        Evaluate the given string against all registered commands and
        return the defined response.

        :type  command: str
        :param command: The command that is evaluated.
        :rtype:  str or None
        :return: The response, if one was defined.
        :raises ValueError: Raised when the command is undefined (strict mode only).
        """
        for cmd, response in self.response_list:
            if not cmd.match(command):
                continue
            if response is None:
                return None
            elif callable(response):
                return response(command)
            else:
                return response
        if self.strict:
            raise ValueError('Undefined command: ' + repr(command))
        return None
