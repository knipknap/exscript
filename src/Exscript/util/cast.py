# Copyright (C) 2007-2010 Samuel Abels.
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
"""
Handy shortcuts for converting types.
"""
from Exscript.Host    import Host
from Exscript.Log     import Log
from Exscript.Logfile import Logfile

def to_list(item):
    """
    If the given item is iterable, this function returns the given item.
    If the item is not iterable, this function returns a list with only the
    item in it.

    @type  item: object
    @param item: Any object.
    @rtype:  list
    @return: A list with the item in it.
    """
    if hasattr(item, '__iter__'):
        return item
    return [item]

def to_host(host, default_protocol = 'telnet', default_domain = ''):
    """
    Given a string or a Host object, this function returns a Host object.

    @type  host: string|Host
    @param host: A hostname (may be URL formatted) or a Host object.
    @type  default_protocol: str
    @param default_protocol: Passed to the Host constructor.
    @type  default_domain: str
    @param default_domain: Appended to each hostname that has no domain.
    @rtype:  Host
    @return: The Host object.
    """
    if host is None:
        raise TypeError('None can not be cast to Host')
    if hasattr(host, 'get_address'):
        return host
    if default_domain and not '.' in host:
        host += '.' + default_domain
    return Host(host)

def to_hosts(hosts, default_protocol = 'telnet', default_domain = ''):
    """
    Given a string or a Host object, or a list of strings or Host objects,
    this function returns a list of Host objects.

    @type  hosts: string|Host|list(string)|list(Host)
    @param hosts: One or more hosts or hostnames.
    @type  default_protocol: str
    @param default_protocol: Passed to the Host constructor.
    @type  default_domain: str
    @param default_domain: Appended to each hostname that has no domain.
    @rtype:  list[Host]
    @return: A list of Host objects.
    """
    return [to_host(h, default_protocol, default_domain)
            for h in to_list(hosts)]

def to_log(log):
    """
    Given a string, this function returns a new Logfile object.
    Given any other Log object, this function just returns the same object.

    @type  log: string|Log
    @param log: A logfile name or a Log object.
    @rtype:  Log
    @return: The Log object.
    """
    if log is None:
        raise TypeError('None can not be cast to Log')
    if isinstance(log, Log):
        return log
    return Logfile(log)

def to_logs(logs):
    """
    Given a string or a Log object, or a list of strings or Log objects,
    this function returns a list of Log objects.

    @type  logs: string|Log|list(string)|list(Log)
    @param logs: One or more logs or logfile names.
    @rtype:  list[Log]
    @return: A list of Log objects.
    """
    return [to_log(h) for h in to_list(logs)]
