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
Handy shortcuts for converting types.
"""

import re
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, cast

import Exscript

if TYPE_CHECKING:
    from ..host import Host


# Returns Any: an iterable item is returned as it is, so the type of the
# result depends on the type of the item.
def to_list(item: object) -> Any:
    """
    If the given item is iterable, this function returns the given item.
    If the item is not iterable, this function returns a list with only the
    item in it. A string counts as not iterable.

    :type  item: object
    :param item: Any object.
    :rtype:  list|Iterable
    :return: The item, or a list with the item in it.
    """
    if hasattr(item, '__iter__') and not isinstance(item, str):
        return item
    return [item]


def to_host(host: 'str | Host', default_protocol: str = 'ssh', default_domain: str = '') -> 'Host':
    """
    Given a string or a Host object, this function returns a Host object.
    Raises TypeError if the host is None.

    :type  host: string|Host
    :param host: A hostname (may be URL formatted) or a Host object.
    :type  default_protocol: str
    :param default_protocol: Passed to the Host constructor.
    :type  default_domain: str
    :param default_domain: Appended to each hostname that has no domain.
    :rtype:  Host
    :return: The Host object.
    """
    if host is None:
        raise TypeError('None can not be cast to Host')
    if hasattr(host, 'get_address'):
        return cast('Host', host)  # any object with get_address() counts as a Host
    if default_domain and '.' not in host:
        host += '.' + default_domain
    return Exscript.Host(host, default_protocol=default_protocol)


def to_hosts(
    hosts: 'str | Host | Iterable[str | Host]',
    default_protocol: str = 'ssh',
    default_domain: str = '',
) -> 'list[Host]':
    """
    Given a string or a Host object, or a list of strings or Host objects,
    this function returns a list of Host objects.

    :type  hosts: string|Host|list(string)|list(Host)
    :param hosts: One or more hosts or hostnames.
    :type  default_protocol: str
    :param default_protocol: Passed to the Host constructor.
    :type  default_domain: str
    :param default_domain: Appended to each hostname that has no domain.
    :rtype:  list[Host]
    :return: A list of Host objects.
    """
    return [to_host(h, default_protocol, default_domain) for h in to_list(hosts)]


def to_regex(regex: str | re.Pattern[str], flags: int = 0) -> re.Pattern[str]:
    """
    Given a string, this function returns a new re.Pattern.
    Given a re.Pattern, this function just returns the same object.
    Raises TypeError if the regex is None.

    :type  regex: string|re.Pattern
    :param regex: A regex or a re.Pattern
    :type  flags: int
    :param flags: See Python's re.compile().
    :rtype:  re.Pattern
    :return: The Python regex object.
    """
    if regex is None:
        raise TypeError('None can not be cast to re.RegexObject')
    if hasattr(regex, 'match'):
        return cast('re.Pattern[str]', regex)  # any object with match() counts as compiled
    return re.compile(regex, flags)


def to_regexs(
    regexs: str | re.Pattern[str] | Iterable[str | re.Pattern[str]],
) -> list[re.Pattern[str]]:
    """
    Given a string or a re.Pattern, or a list of strings or
    re.Patterns, this function returns a list of re.Patterns.

    :type  regexs: str|re.Pattern|list(str|re.Pattern)
    :param regexs: One or more regexs or re.Patterns.
    :rtype:  list(re.Pattern)
    :return: A list of re.Patterns.
    """
    return [to_regex(r) for r in to_list(regexs)]
