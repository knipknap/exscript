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
IPv4 address calculation and conversion.
"""

import math
import re
import socket
import struct
from collections.abc import Iterable
from typing import cast


def _least_bit(number: int) -> int:
    """
    Returns the position of the lowest bit that is set in the given 32-bit
    number, or 32 if no bit is set.
    """
    for i in range(0, 32):
        if number & (0x00000001 << i) != 0:
            return i
    return 32


def _highest_bit(number: int) -> float:
    """
    Rounds the given 32-bit number up to the next power of two and returns
    the square root of the result; returns 0 for 0.
    """
    if number == 0:
        return 0
    number -= 1
    number |= number >> 1
    number |= number >> 2
    number |= number >> 4
    number |= number >> 8
    number |= number >> 16
    number += 1
    return math.sqrt(number)


def is_ip(string: str) -> bool:
    """
    Returns True if the given string is an IPv4 address, False otherwise.

    :type  string: string
    :param string: Any string.
    :rtype:  bool
    :return: True if the string is an IP address, False otherwise.
    """
    mo = re.match(r'(\d+)\.(\d+)\.(\d+)\.(\d+)\Z', string)
    if mo is None:
        return False
    for group in mo.groups():
        if int(group) not in list(range(0, 256)):
            return False
    return True


def normalize_ip(ip: str) -> str:
    """
    Transform the address into a fixed-length form, such as::

        192.168.0.1 -> 192.168.000.001

    :type  ip: string
    :param ip: An IP address.
    :rtype:  string
    :return: The normalized IP.
    """
    theip = ip.split('.')
    if len(theip) != 4:
        raise ValueError('ip should be 4 tuples')
    return '.'.join(str(int(l)).rjust(3, '0') for l in theip)


def clean_ip(ip: str) -> str:
    """
    Cleans the ip address up, useful for removing leading zeros, e.g.::

        192.168.010.001 -> 192.168.10.1

    :type  ip: string
    :param ip: An IP address.
    :rtype:  string
    :return: The cleaned up IP.
    """
    return '.'.join(str(int(i)) for i in ip.split('.'))


def ip2int(ip: str) -> int:
    """
    Converts the given IP address to a 4 byte integer value.

    :type  ip: string
    :param ip: An IP address.
    :rtype:  int
    :return: The IP, converted to a number.
    """
    if ip == '255.255.255.255':
        return 0xFFFFFFFF
    return cast(int, struct.unpack('!L', socket.inet_aton(ip))[0])


def int2ip(number: int) -> str:
    """
    Converts the given integer value to an IP address.

    :type  number: int
    :param number: An IP as a number.
    :rtype:  string
    :return: The IP address.
    """
    number &= 0xFFFFFFFF
    return socket.inet_ntoa(struct.pack('!L', number))


def pfxlen2mask_int(pfxlen: int) -> int:
    """
    Converts the given prefix length to an IP mask value.

    :type  pfxlen: int
    :param pfxlen: A prefix length.
    :rtype:  int
    :return: The mask, as an integer.
    """
    return 0xFFFFFFFF << (32 - int(pfxlen))


def pfxlen2mask(pfxlen: int) -> str:
    """
    Converts the given prefix length to an IP mask.

    :type  pfxlen: int
    :param pfxlen: A prefix length.
    :rtype:  string
    :return: The mask.
    """
    return int2ip(pfxlen2mask_int(pfxlen))


def mask2pfxlen(mask: str) -> int:
    """
    Converts the given IP mask to a prefix length.

    :type  mask: string
    :param mask: An IP mask.
    :rtype:  int
    :return: The prefix length.
    """
    return 32 - _least_bit(ip2int(mask))


def parse_prefix(prefix: str, default_length: int = 24) -> tuple[str, int]:
    """
    Splits the given IP prefix into a network address and a prefix length.
    If the prefix does not have a length (i.e., it is a simple IP address),
    it is presumed to have the given default length.

    :type  prefix: string
    :param prefix: An IP prefix.
    :type  default_length: int
    :param default_length: The default ip prefix length.
    :rtype:  string, int
    :return: A tuple containing the IP address and prefix length.
    """
    pfxlen: str | int
    if '/' in prefix:
        network, pfxlen = prefix.split('/')
    else:
        network = prefix
        pfxlen = default_length
    return network, int(pfxlen)


def network(prefix: str, default_length: int = 24) -> str:
    """
    Given a prefix, this function returns the corresponding network
    address.

    :type  prefix: string
    :param prefix: An IP prefix.
    :type  default_length: int
    :param default_length: The default ip prefix length.
    :rtype:  string
    :return: The IP network address.
    """
    address, pfxlen = parse_prefix(prefix, default_length)
    ip = ip2int(address)
    return int2ip(ip & pfxlen2mask_int(pfxlen))


def broadcast(prefix: str, default_length: int = 24) -> str:
    """
    Given a prefix, this function returns the corresponding broadcast
    address.

    :type  prefix: string
    :param prefix: An IP prefix.
    :type  default_length: int
    :param default_length: The default ip prefix length.
    :rtype:  string
    :return: The IP broadcast address.
    """
    address, pfxlen = parse_prefix(prefix, default_length)
    ip = ip2int(address)
    return int2ip(ip | ~pfxlen2mask_int(pfxlen))


def remote_ip(local_ip: str) -> str:
    """
    Given an IP address, this function calculates the remaining available
    IP address under the assumption that it is a /30 network.
    In other words, given one link net address, this function returns the
    other link net address.

    :type  local_ip: string
    :param local_ip: An IP address.
    :rtype:  string
    :return: The other IP address of the link address pair.
    """
    ip_int = ip2int(local_ip)
    network = ip_int & pfxlen2mask_int(30)
    return int2ip(network + 3 - (ip_int - network))


def matches_prefix(ip: str, prefix: str) -> bool:
    """
    Returns True if the given IP address is part of the given
    network, returns False otherwise.

    :type  ip: string
    :param ip: An IP address.
    :type  prefix: string
    :param prefix: An IP prefix.
    :rtype:  bool
    :return: True if the IP is in the prefix, False otherwise.
    """
    ip_int = ip2int(ip)
    network, pfxlen = parse_prefix(prefix)
    network_int = ip2int(network)
    mask_int = pfxlen2mask_int(pfxlen)
    return ip_int & mask_int == network_int & mask_int


def is_private(ip: str) -> bool:
    """
    Returns True if the given IP address is private,
    returns False otherwise.

    :type  ip: string
    :param ip: An IP address.
    :rtype:  bool
    :return: True if the IP is private, False otherwise.
    """
    if matches_prefix(ip, '10.0.0.0/8'):
        return True
    if matches_prefix(ip, '172.16.0.0/12'):
        return True
    if matches_prefix(ip, '192.168.0.0/16'):
        return True
    return False


def sort(iterable: Iterable[str]) -> list[str]:
    """
    Given an IP address list, this function sorts the list.

    :type  iterable: Iterator
    :param iterable: An IP address list.
    :rtype:  list
    :return: The sorted IP address list.
    """
    ips = sorted(normalize_ip(ip) for ip in iterable)
    return [clean_ip(ip) for ip in ips]
