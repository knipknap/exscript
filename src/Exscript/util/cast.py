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
from Exscript.Host    import Host
from Exscript.Log     import Log
from Exscript.Logfile import Logfile

def to_host(host):
    """
    Given a string or a Host object, this function returns a Host object.

    @type  host: string|Host
    @param host: A hostname (may be URL formatted) or a Host object.
    @rtype:  Host
    @return: The Host object.
    """
    if host is None:
        raise TypeError('None can not be cast to Host')
    if isinstance(host, Host):
        return host
    return Host(host)

def to_hosts(hosts):
    """
    Given a string or a Host object, or a list of strings or Host objects,
    this function returns a list of Host objects.

    @type  host: string|Host|list(string)|list(Host)
    @param host: One or more hosts or hostnames.
    @rtype:  list[Host]
    @return: A list of Host objects.
    """
    if not hasattr(hosts, '__iter__'):
        hosts = [hosts]
    return [to_host(h) for h in hosts]

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

    @type  log: string|Log|list(string)|list(Log)
    @param log: One or more logs or logfile names.
    @rtype:  list[Log]
    @return: A list of Log objects.
    """
    if not hasattr(logs, '__iter__'):
        logs = [logs]
    return [to_log(h) for h in logs]
