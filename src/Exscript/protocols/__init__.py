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
The protocol adapters, and functions that create them by the name of the
protocol or from a URL.
"""

from typing import TYPE_CHECKING, Any, cast

from .. import Account
from ..util.cast import to_host
from ..util.url import Url
from .dummy import Dummy
from .netconf import Netconf
from .protocol import Protocol
from .ssh2 import SSH2
from .telnet import Telnet

if TYPE_CHECKING:
    from ..host import Host

protocol_map: dict[str, type[Protocol]] = {
    'dummy': Dummy,
    'pseudo': Dummy,
    'telnet': Telnet,
    'ssh': SSH2,
    'ssh2': SSH2,
    'netconf': Netconf,
}


def get_protocol_from_name(name: str) -> type[Protocol]:
    """
    Returns the protocol class for the protocol with the given name.

    :type  name: str
    :param name: The name of the protocol.
    :rtype:  type[Protocol]
    :return: The protocol class.
    """
    cls = protocol_map.get(name)
    if not cls:
        raise ValueError('Unsupported protocol "%s".' % name)
    return cls


def create_protocol(name: str, **kwargs: Any) -> Protocol:
    """
    Returns an instance of the protocol with the given name.

    :type  name: str
    :param name: The name of the protocol.
    :rtype:  Protocol
    :return: An instance of the protocol.
    """
    cls = protocol_map.get(name)
    if not cls:
        raise ValueError('Unsupported protocol "%s".' % name)
    return cls(**kwargs)


def prepare(host: 'str | Host', default_protocol: str = 'ssh', **kwargs: Any) -> Protocol:
    """
    Creates an instance of the protocol by either parsing the given
    URL-formatted hostname using :class:`Exscript.util.url`, or according to
    the options of the given :class:`Exscript.Host`.

    :type  host: str or Host
    :param host: A URL-formatted hostname or a :class:`Exscript.Host` instance.
    :type  default_protocol: str
    :param default_protocol: Protocol that is used if the URL specifies none.
    :type  kwargs: dict
    :param kwargs: Passed to the protocol constructor.
    :rtype:  Protocol
    :return: An instance of the protocol.
    """
    host = to_host(host, default_protocol=default_protocol)
    protocol = host.get_protocol()
    conn = create_protocol(protocol, **kwargs)
    if protocol == 'pseudo':
        filename = host.get_address()
        # protocol_map maps 'pseudo' to Dummy.
        cast(Dummy, conn).device.add_commands_from_file(filename)
    return conn


def connect(host: 'str | Host', default_protocol: str = 'ssh', **kwargs: Any) -> Protocol:
    """
    Like :class:`prepare()`, but also connects to the host by calling
    :class:`Protocol.connect()`. If the URL or host contain any login info, this
    function also logs into the host using :class:`Protocol.login()`.

    :type  host: str or Host
    :param host: A URL-formatted hostname or a :class:`Exscript.Host` object.
    :type  default_protocol: str
    :param default_protocol: Protocol that is used if the URL specifies none.
    :type  kwargs: dict
    :param kwargs: Passed to the protocol constructor.
    :rtype:  Protocol
    :return: An instance of the protocol.
    """
    host = to_host(host)
    conn = prepare(host, default_protocol, **kwargs)
    account = host.get_account()
    conn.connect(host.get_address(), host.get_tcp_port())
    if account is not None:
        conn.login(account)
    return conn


__all__ = [
    'Account',
    'to_host',
    'Url',
    'Dummy',
    'Netconf',
    'Protocol',
    'SSH2',
    'Telnet',
    'protocol_map',
    'get_protocol_from_name',
    'create_protocol',
    'prepare',
    'connect',
]
