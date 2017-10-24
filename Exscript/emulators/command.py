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
from past.builtins import execfile
from builtins import str
from builtins import object
import re


class CommandSet(object):

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

    def add(self, command, response):
        """
        Register a command/response pair.

        The command may be either a string (which is then automatically
        compiled into a regular expression), or a pre-compiled regular
        expression object.

        If the given response handler is a string, it is sent as the
        response to any command that matches the given regular expression.
        If the given response handler is a function, it is called
        with the command passed as an argument.

        :type  command: str|regex
        :param command: A string or a compiled regular expression.
        :type  response: function|str
        :param response: A reponse, or a response handler.
        """
        command = re.compile(command)
        self.response_list.append((command, response))

    def add_from_file(self, filename, handler_decorator=None):
        """
        Wrapper around add() that reads the handlers from the
        file with the given name. The file is a Python script containing
        a list named 'commands' of tuples that map command names to
        handlers.

        :type  filename: str
        :param filename: The name of the file containing the tuples.
        :type  handler_decorator: function
        :param handler_decorator: A function that is used to decorate
               each of the handlers in the file.
        """
        args = {}
        execfile(filename, args)
        commands = args.get('commands')
        if commands is None:
            raise Exception(filename + ' has no variable named "commands"')
        elif not hasattr(commands, '__iter__'):
            raise Exception(filename + ': "commands" is not iterable')
        for key, handler in commands:
            if handler_decorator:
                handler = handler_decorator(handler)
            self.add(key, handler)

    def eval(self, command):
        """
        Evaluate the given string against all registered commands and
        return the defined response.

        :type  command: str
        :param command: The command that is evaluated.
        :rtype:  str or None
        :return: The response, if one was defined.
        """
        for cmd, response in self.response_list:
            if not cmd.match(command):
                continue
            if response is None:
                return None
            elif hasattr(response, '__call__'):
                return response(command)
            else:
                return response
        if self.strict:
            raise Exception('Undefined command: ' + repr(command))
        return None
