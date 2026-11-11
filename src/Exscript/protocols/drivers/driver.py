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
Base class for all drivers.
"""

import re
import string
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ...account import Account
    from ...util.impl import _Context
    from ..protocol import Protocol

_flags = re.I
_printable = re.escape(string.printable)
_unprintable = r'[^' + _printable + r']'
_ignore = r'[\x1b\x07\x00]'
_nl = r'(?:\r\n|[\r\n])'
_prompt_start = _nl + r'(?:' + _unprintable + r'*|' + _ignore + '*)'
# A prompt like "[user@host:~/path (config)]#", where most parts are optional.
# The runs of name characters are matched possessively (++, *+): the parts are
# separated by @, :, ~, / or a space, so a run never needs to be split. This
# keeps the time linear on long lines that are no prompt.
_name = r'[\w+\-.]'
_path = r'~?' + _name + r'*+(?:/' + _name + r'++)*+/?'
_prompt_re = [
    re.compile(
        _prompt_start
        + r'[\[\<]?'
        + r'\w(?:[\w+\-]++@'  # user@host, at least two characters before the @
        + _name
        + r'++|'
        + _name
        + r'*+)'
        + r':?'
        + _path
        + r'[: ]?'
        + _path
        + r'(?:\('
        + _name
        + r'++\))?'
        + r'[\]\-]?'
        + r'[#>%\$\]] ?'
        + _unprintable
        + r'*'
        + r'\Z',
        _flags,
    ),
]

_user_re = [re.compile(r'(user ?name|user|login): *$', _flags)]
_pass_re = [re.compile(r'password:? *$', _flags)]
_errors = [
    r'error',
    r'invalid',
    r'incomplete',
    r'unrecognized',
    r'unknown command',
    r'connection timed out',
    r'[^\r\n]+ not found',
]
_error_re = [re.compile(r'^%?\s*(?:' + '|'.join(_errors) + r')', _flags)]
_login_fail = [
    r'bad secrets',
    r'denied',
    r'invalid',
    r'too short',
    r'incorrect',
    r'connection timed out',
    r'failed',
    r'failure',
]
_login_fail_re = [
    re.compile(_nl + r'[^\r\n]*' + r'(?:' + '|'.join(_login_fail) + r')', _flags),
]
_netconf_prompt_re = [
    re.compile(
        r'(?<=>)'  # any XML closing tag (generic)
        + r'[ \t\r\n]*'
        + r'(?:]]>]]>|\n##\n)'  # 1.0 EOM or 1.1 EOC sequence
        + r'[ \t\r\n]*'
        + _unprintable
        + r'*'
        + r'\Z',
        _flags,
    ),
]
_netconf_error_re = [re.compile(r'<(?:[\w.\-]+:)?rpc-error[\s/>]', _flags)]


class Driver:
    """
    The base class of all drivers. A driver holds what is specific to one
    operating system: the patterns of its prompts and error messages, how it
    is recognized, and how a session is prepared, authorized and ended. The
    generic driver uses this class unchanged; its patterns work with many
    devices.
    """

    def __init__(self, name: str) -> None:
        """
        Constructor. Sets the generic patterns; subclasses replace those that
        differ.

        :param name: The name of the driver, which is also the name of the
            operating system that guess_os() returns and set_driver() accepts.
        """
        self.name = name
        self.user_re = _user_re
        self.password_re = _pass_re
        self.prompt_re = _prompt_re
        self.error_re = _error_re
        self.login_error_re = _login_fail_re
        # SSH2 related:
        self.reconnect_between_auth_methods = False
        # Netconf related:
        self.netconf_device_params: dict[str, Any] = {}  # see ncclient documentation
        # used to determine vendor/OS driver
        self.netconf_capabilities_re: list[re.Pattern[str]] = []
        self.netconf_prompt_re = _netconf_prompt_re
        self.netconf_error_re = _netconf_error_re

    def __repr__(self) -> str:
        return f"{type(self).__name__}('{self.name}')"

    def supports_os_guesser(self) -> bool:
        """
        Returns whether the driver overrides one of check_protocol_for_os(),
        check_head_for_os() and check_response_for_os(), i.e. whether the OS
        guesser can recognize its operating system.
        """
        return (
            self.check_protocol_for_os.__code__ is not Driver.check_protocol_for_os.__code__
            or self.check_head_for_os.__code__ is not Driver.check_head_for_os.__code__
            or self.check_response_for_os.__code__ is not Driver.check_response_for_os.__code__
        )

    def check_protocol_for_os(self, string: str) -> int:
        """
        Returns the confidence, from 0 to 100, that the given protocol
        information, e.g. the SSH version string, comes from the operating
        system of this driver. The base class returns 0.
        """
        return 0

    def _check_protocol(self, string: str) -> tuple[str, int]:
        """
        Returns the name of the driver and the result of
        check_protocol_for_os() for the given string.
        """
        return self.name, self.check_protocol_for_os(string)

    def check_netconf_capabilities(self, string: str) -> int:
        """
        Returns 100 if one of the netconf_capabilities_re patterns matches the
        given NETCONF capabilities (one per line), else 0.
        """
        if not self.netconf_capabilities_re:
            return 0
        for regex in self.netconf_capabilities_re:
            if regex.search(string):
                return 100
        return 0

    def _check_netconf(self, string: str) -> tuple[str, int]:
        """
        Returns the name of the driver and the result of
        check_netconf_capabilities() for the given string.
        """
        return self.name, self.check_netconf_capabilities(string)

    def check_head_for_os(self, string: str) -> int:
        """
        Returns the confidence, from 0 to 100, that the given data, which the
        host sent up to the end of the login, comes from the operating system
        of this driver. The base class returns 0.
        """
        return 0

    def _check_head(self, string: str) -> tuple[str, int]:
        """
        Returns the name of the driver and the result of check_head_for_os()
        for the given string.
        """
        return self.name, self.check_head_for_os(string)

    def check_response_for_os(self, string: str) -> int:
        """
        Returns the confidence, from 0 to 100, that the given data, which the
        host sent, e.g. a prompt, comes from the operating system of this
        driver. The base class returns 0.
        """
        return 0

    def _check_response(self, string: str) -> tuple[str, int]:
        """
        Returns the name of the driver and the result of
        check_response_for_os() for the given string.
        """
        return self.name, self.check_response_for_os(string)

    def clean_response_for_re_match(self, response: str) -> tuple[str, str]:
        """
        Prepares the end of the received data for matching the prompt
        patterns that end with $ or \\Z, e.g. by removing control sequences.
        The base class returns the data unchanged.

        :param response: The end of the received data.
        :return: The cleaned data, and the incomplete rest at its end that is
            not matched, e.g. the start of an escape sequence.
        """
        return response, ''

    def init_terminal(self, conn: 'Protocol') -> None:
        """
        Prepares the session on the given connection for scripts, e.g. turns
        off the pager. The base class does nothing.
        """
        pass

    def supports_auto_authorize(self) -> bool:
        """
        Returns whether auto_authorize() sends a command that starts the
        authorization, such as "enable", so that login() consumes the prompt
        before it calls auto_authorize(). By default, this is whether the
        driver overrides auto_authorize(); a driver whose auto_authorize()
        sends nothing returns False.
        """
        return self.__class__.auto_authorize is not Driver.auto_authorize

    def auto_authorize(
        self,
        conn: 'Protocol',
        account: 'Account | _Context | None',
        flush: bool,
        bailout: bool,
    ) -> None:
        """
        Gets the privileges that commands need, e.g. with "enable". The base
        class calls conn.app_authorize(); the arguments are those of
        Protocol.app_authorize().
        """
        conn.app_authorize(account, flush, bailout)

    def logout(self, conn: 'Protocol') -> None:
        """
        Ends the session on the given connection. The base class sends "exit".
        """
        conn.send('exit\r')
