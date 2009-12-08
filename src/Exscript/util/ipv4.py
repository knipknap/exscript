# Copyright (C) 2007-2009 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import socket, struct, math, re

def _least_bit(number):
    for n in range(0, 31):
        if number & (0x00000001l << n) != 0:
            return n + 1
    return 0

def _highest_bit(number):
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

def is_ip(string):
    """
    Returns True if the given string is an IPv4 address, False otherwise.

    @type  string: string
    @param string: Any string.
    @rtype:  bool
    @return: True if the string is an IP address, False otherwise.
    """
    return re.match(r'\d+\.\d+\.\d+\.\d+', string) and True or False

def ip2int(ip):
    """
    Converts the given IP address to a 4 byte integer value.

    @type  ip: string
    @param ip: An IP address.
    @rtype:  long
    @return: The IP, converted to a number.
    """
    if ip == '255.255.255.255':
        return 0xFFFFFFFFl
    return struct.unpack('!L', socket.inet_aton(ip))[0]

def int2ip(number):
    """
    Converts the given integer value to an IP address.

    @type  number: long
    @param number: An IP as a number.
    @rtype:  string
    @return: The IP address.
    """
    return socket.inet_ntoa(struct.pack('!L', number))

def pfxlen2mask_int(pfxlen):
    """
    Converts the given prefix length to an IP mask value.

    @type  pfxlen: int
    @param pfxlen: A prefix length.
    @rtype:  long
    @return: The mask, as a long value.
    """
    return 0xFFFFFFFFl << (32 - int(pfxlen))

def pfxlen2mask(pfxlen):
    """
    Converts the given prefix length to an IP mask.

    @type  pfxlen: int
    @param pfxlen: A prefix length.
    @rtype:  string
    @return: The mask.
    """
    return int2ip(pfxlen2mask(pfxlen))

def mask2pfxlen(mask):
    """
    Converts the given IP mask to a prefix length.

    @type  mask: string
    @param mask: An IP mask.
    @rtype:  long
    @return: The mask, as a long value.
    """
    mask_int = ip2int(mask)
    return 33 - _least_bit(mask_int)

def parse_prefix(prefix, default_length = 24):
    """
    Splits the given IP prefix into a network address and a prefix length.
    If the prefix does not have a length (i.e., it is a simple IP address),
    it is presumed to have the given default length.

    @type  prefix: string
    @param prefix: An IP mask.
    @type  default_length: long
    @param default_length: The default ip prefix length.
    @rtype:  string, int
    @return: A tuple containing the IP address and prefix length.
    """
    if '/' in prefix:
        network, pfxlen = prefix.split('/')
    else:
        network = prefix
        pfxlen  = default_length
    return ip2int(network), int(pfxlen)

def remote_ip(local_ip):
    """
    Given an IP address, this function calculates the remaining available
    IP address under the assumption that it is a /30 network.
    In other words, given one link net address, this function returns the
    other link net address.

    @type  local_ip: string
    @param local_ip: An IP address.
    @rtype:  string
    @return: The other IP address of the link address pair.
    """
    local_ip = ip2int(local_ip)
    network  = local_ip & pfxlen2mask(30)
    return int2ip(network + 3 - (local_ip - network))
