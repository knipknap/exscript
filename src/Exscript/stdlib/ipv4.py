# Copyright (C) 2007 Samuel Abels, http://debain.org
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
from Exscript.util import ipv4

True  = 1
False = 0

def in_network(scope, prefixes, destination, default_mask = [24]):
    needle = ipv4.ip2int(destination[0])
    for prefix in prefixes:
        network, pfxlen = ipv4.parse_prefix(prefix, default_mask[0])
        mask            = ipv4.pfxlen2mask(pfxlen)
        if needle & mask == network & mask:
            return [True]
    return [False]

def mask(scope, ips, mask):
    mask = ipv4.ip2int(mask[0])
    return [ipv4.int2ip(ipv4.ip2int(ip) & mask) for ip in ips]

def mask2pfxlen(scope, masks):
    return [ipv4.mask2pfxlen(mask) for mask in masks]

def pfxlen2mask(scope, pfxlen):
    return [ipv4.pfxlen2mask(pfx) for pfx in pfxlen]

def pfxmask(scope, ips, pfxlens):
    mask = ipv4.pfxlen2mask(pfxlens[0])
    return [ipv4.int2ip(ipv4.ip2int(ip) & mask) for ip in ips]

def remote_ip(scope, local_ips):
    return [ipv4.remote_ip(ip) for ip in local_ips]
