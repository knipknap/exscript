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
Wrapper around the ipv4 and ipv6 modules to handle both, ipv4 and ipv6.
"""
from Exscript.util import ipv4
from Exscript.util import ipv6


def is_ip(string):
    """
    Returns True if the given string is an IPv4 or IPv6 address, False
    otherwise.

    :type  string: string
    :param string: Any string.
    :rtype:  bool
    :return: True if the string is an IP address, False otherwise.
    """
    return ipv4.is_ip(string) or ipv6.is_ip(string)


def _call_func(funcname, ip, *args):
    if ipv4.is_ip(ip):
        return ipv4.__dict__[funcname](ip, *args)
    elif ipv6.is_ip(ip):
        return ipv6.__dict__[funcname](ip, *args)
    raise ValueError('neither ipv4 nor ipv6: ' + repr(ip))


def normalize_ip(ip):
    """
    Transform the address into a fixed-length form, such as:

        192.168.0.1 -> 192.168.000.001
        1234::A -> 1234:0000:0000:0000:0000:0000:0000:000a

    :type  ip: string
    :param ip: An IP address.
    :rtype:  string
    :return: The normalized IP.
    """
    return _call_func('normalize_ip', ip)


def clean_ip(ip):
    """
    Cleans the ip address up, useful for removing leading zeros, e.g.::

        192.168.010.001 -> 192.168.10.1
        1234:0000:0000:0000:0000:0000:0000:000A -> 1234::a

    :type  ip: string
    :param ip: An IP address.
    :rtype:  string
    :return: The cleaned up IP.
    """
    return _call_func('clean_ip', ip)
