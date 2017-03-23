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
Defines the behavior of a device, as needed by :class:`Exscript.servers`.
"""
from __future__ import absolute_import, unicode_literals
from builtins import range
from builtins import object
from builtins import str
from . import CommandSet


class VirtualDevice(object):

    """
    An object that emulates a remote device.
    """
    LOGIN_TYPE_PASSWORDONLY, \
        LOGIN_TYPE_USERONLY, \
        LOGIN_TYPE_BOTH, \
        LOGIN_TYPE_NONE = list(range(1, 5))

    PROMPT_STAGE_USERNAME, \
        PROMPT_STAGE_PASSWORD, \
        PROMPT_STAGE_CUSTOM = list(range(1, 4))

    def __init__(self,
                 hostname,
                 echo=True,
                 login_type=LOGIN_TYPE_BOTH,
                 strict=True,
                 banner=None):
        """
        :type  hostname: str
        :param hostname: The hostname, used for the prompt.

        :param echo: bool
        :keyword echo: whether to echo the command in a response.
        :param login_type: int
        :keyword login_type: integer constant, one of LOGIN_TYPE_PASSWORDONLY,
            LOGIN_TYPE_USERONLY, LOGIN_TYPE_BOTH, LOGIN_TYPE_NONE.
        :param strict: bool
        :keyword strict: Whether to raise when a given command has no handler.
        :param banner: str
        :keyword banner: A string to show as soon as the connection is opened.
        """
        self.hostname = str(hostname)
        self.banner = str(banner or 'Welcome to %s!\n' % hostname)
        self.echo = echo
        self.login_type = int(login_type)
        self.prompt = str(hostname + '> ')
        self.logged_in = False
        self.commands = CommandSet(strict=strict)
        self.user_prompt = 'User: '
        self.password_prompt = 'Password: '
        self.init()

    def _get_prompt(self):
        if self.prompt_stage == self.PROMPT_STAGE_USERNAME:
            if self.login_type == self.LOGIN_TYPE_USERONLY:
                self.prompt_stage = self.PROMPT_STAGE_CUSTOM
            else:
                self.prompt_stage = self.PROMPT_STAGE_PASSWORD
            return self.user_prompt
        elif self.prompt_stage == self.PROMPT_STAGE_PASSWORD:
            self.prompt_stage = self.PROMPT_STAGE_CUSTOM
            return self.password_prompt
        elif self.prompt_stage == self.PROMPT_STAGE_CUSTOM:
            self.logged_in = True
            return self.prompt
        else:
            raise Exception('invalid prompt stage')

    def _create_autoprompt_handler(self, handler):
        if hasattr(handler, '__call__'):
            return lambda x: handler(x) + '\n' + self._get_prompt()
        else:
            return lambda x: handler + '\n' + self._get_prompt()

    def get_prompt(self):
        """
        Returns the prompt of the device.

        :rtype:  str
        :return: The current command line prompt.
        """
        return self.prompt

    def set_prompt(self, prompt):
        """
        Change the prompt of the device.

        :type  prompt: str
        :param prompt: The new command line prompt.
        """
        self.prompt = prompt

    def add_command(self, command, handler, prompt=True):
        """
        Registers a command.

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
        :param handler: A string, or a response handler.
        :type  prompt: bool
        :param prompt: Whether to show a prompt after completing the command.
        """
        if prompt:
            thehandler = self._create_autoprompt_handler(handler)
        else:
            thehandler = handler
        self.commands.add(command, thehandler)

    def add_commands_from_file(self, filename, autoprompt=True):
        """
        Wrapper around add_command_handler that reads the handlers from the
        file with the given name. The file is a Python script containing
        a list named 'commands' of tuples that map command names to
        handlers.

        :type  filename: str
        :param filename: The name of the file containing the tuples.
        :type  autoprompt: bool
        :param autoprompt: Whether to append a prompt to each response.
        """
        if autoprompt:
            deco = self._create_autoprompt_handler
        else:
            deco = None
        self.commands.add_from_file(filename, deco)

    def init(self):
        """
        Init or reset the virtual device.

        :rtype:  str
        :return: The initial response of the virtual device.
        """
        self.logged_in = False

        if self.login_type == self.LOGIN_TYPE_PASSWORDONLY:
            self.prompt_stage = self.PROMPT_STAGE_PASSWORD
        elif self.login_type == self.LOGIN_TYPE_NONE:
            self.prompt_stage = self.PROMPT_STAGE_CUSTOM
        else:
            self.prompt_stage = self.PROMPT_STAGE_USERNAME

        return self.banner + self._get_prompt()

    def do(self, command):
        """
        "Executes" the given command on the virtual device, and returns
        the response.

        :type  command: str
        :param command: The command to be executed.
        :rtype:  str
        :return: The response of the virtual device.
        """
        echo = self.echo and command or ''
        if not self.logged_in:
            return echo + '\n' + self._get_prompt()

        response = self.commands.eval(command)
        if response is None:
            return echo + '\n' + self._get_prompt()
        return echo + response
