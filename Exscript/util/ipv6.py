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
IPv6 address calculation and conversion.
"""
from builtins import range


def is_ip(string):
    """
    Returns True if the given string is an IPv6 address, False otherwise.

    :type  string: string
    :param string: Any string.
    :rtype:  bool
    :return: True if the string is an IP address, False otherwise.
    """
    try:
        normalize_ip(string)
    except ValueError:
        return False
    return True


def normalize_ip(ip):
    """
    Transform the address into a standard, fixed-length form, such as:

        1234:0:01:02:: -> 1234:0000:0001:0002:0000:0000:0000:0000
        1234::A -> 1234:0000:0000:0000:0000:0000:0000:000a

    :type  ip: string
    :param ip: An IP address.
    :rtype:  string
    :return: The normalized IP.
    """
    theip = ip
    if theip.startswith('::'):
        theip = '0' + theip
    if theip.endswith('::'):
        theip += '0'
    segments = theip.split(':')
    if len(segments) == 1:
        raise ValueError('no colons in ipv6 address: ' + repr(ip))
    fill = 8 - len(segments)
    if fill < 0:
        raise ValueError('ipv6 address has too many segments: ' + repr(ip))
    result = []
    for segment in segments:
        if segment == '':
            if fill == 0:
                raise ValueError('unexpected double colon: ' + repr(ip))
            for n in range(fill + 1):
                result.append('0000')
            fill = 0
        else:
            try:
                int(segment, 16)
            except ValueError:
                raise ValueError('invalid hex value in ' + repr(ip))
            result.append(segment.rjust(4, '0'))
    return ':'.join(result).lower()


def clean_ip(ip):
    """
    Cleans the ip address up, useful for removing leading zeros, e.g.::

        1234:0:01:02:: -> 1234:0:1:2::
        1234:0000:0000:0000:0000:0000:0000:000A -> 1234::a
        1234:0000:0000:0000:0001:0000:0000:0000 -> 1234:0:0:0:1::
        0000:0000:0000:0000:0001:0000:0000:0000 -> ::1:0:0:0

    :type  ip: string
    :param ip: An IP address.
    :rtype:  string
    :return: The cleaned up IP.
    """
    theip = normalize_ip(ip)
    segments = ['%x' % int(s, 16) for s in theip.split(':')]

    # Find the longest consecutive sequence of zeroes.
    seq = {0: 0}
    start = None
    count = 0
    for n, segment in enumerate(segments):
        if segment != '0':
            start = None
            count = 0
            continue
        if start is None:
            start = n
        count += 1
        seq[count] = start

    # Replace those zeroes by a double colon.
    count = max(seq)
    start = seq[count]
    result = []
    for n, segment in enumerate(segments):
        if n == start and count > 1:
            if n == 0:
                result.append('')
            result.append('')
            if n == 7:
                result.append('')
            continue
        elif start < n < start + count:
            if n == 7:
                result.append('')
            continue
        result.append(segment)
    return ':'.join(result)


def parse_prefix(prefix, default_length=128):
    """
    Splits the given IP prefix into a network address and a prefix length.
    If the prefix does not have a length (i.e., it is a simple IP address),
    it is presumed to have the given default length.

    :type  prefix: string
    :param prefix: An IP mask.
    :type  default_length: long
    :param default_length: The default ip prefix length.
    :rtype:  string, int
    :return: A tuple containing the IP address and prefix length.
    """
    if '/' in prefix:
        network, pfxlen = prefix.split('/')
    else:
        network = prefix
        pfxlen = default_length
    return network, int(pfxlen)
