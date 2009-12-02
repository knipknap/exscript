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
import re

True  = 1
False = 0

###############################################################
# utils
###############################################################
def _update_host_info(scope, force = False):
    # If the info is cached, return it.
    info = scope.get('_stdlib.device.have_remote_info')
    if info is not None and force:
        return
    scope.define(**{'_stdlib.device.have_remote_info': 1})

    conn = scope.get('__connection__')
    conn.execute('show version')
    response = conn.response.split('\n')[1:]
    for line in response:
        if re.match(r'^JUNOS', line, re.I) is not None:
            conn.remote_info['os']     = 'junos'
            conn.remote_info['vendor'] = 'juniper'
            for line in response:
                match = re.match(r'Model: (.*)', line, re.I)
                if match is not None:
                    conn.remote_info['model'] = match.group(1)
                    break
            break
        match = re.match(r'^Cisco IOS XR', line, re.I)
        if match is not None:
            conn.remote_info['os']     = 'ios_xr'
            conn.remote_info['vendor'] = 'cisco'
            break
        if re.match(r'^cisco', line, re.I) is not None:
            conn.remote_info['os']     = 'ios'
            conn.remote_info['vendor'] = 'cisco'
            break

###############################################################
# public api
###############################################################
def guess_os(scope):
    """
    Guesses the operating system of the connected host.

    The recognition is based on the past conversation that has happened
    on the host; Exscript looks for known patterns and maps them to specific
    operating systems.

    @rtype:  string
    @return: The operating system.
    """
    conn = scope.get('__connection__')
    return [conn.guess_os()]

def model(scope, force = None):
    """
    Guesses the model of the connected host by executing one or more commands.
    If force is True, the commands are re-issued even if the result is still
    cached from a previous call.

    @type  force: bool
    @param force: Whether to ignore the cache.
    @rtype:  string
    @return: The model of the remote device.
    """
    conn = scope.get('__connection__')
    if force is None:
        _update_host_info(scope, False)
    elif force[0]:
        _update_host_info(scope, True)
    return [conn.remote_info['model']]

def os(scope, force = None):
    """
    Guesses the operating system of the connected host by executing one or
    more commands. If force is True, the commands are re-issued even if the
    result is still cached from a previous call.

    @type  force: bool
    @param force: Whether to ignore the cache.
    @rtype:  string
    @return: The operating system of the remote device.
    """
    conn = scope.get('__connection__')
    if force is None:
        _update_host_info(scope, False)
    elif force[0]:
        _update_host_info(scope, True)
    return [conn.remote_info['os']]

def vendor(scope, force = None):
    """
    Guesses the vendor of the connected host by executing one or more
    commands. If force is True, the commands are re-issued even if the result
    is still cached from a previous call.

    @type  force: bool
    @param force: Whether to ignore the cache.
    @rtype:  string
    @return: The vendor of the remote device.
    """
    conn = scope.get('__connection__')
    if force is None:
        _update_host_info(scope, False)
    elif force[0]:
        _update_host_info(scope, True)
    return [conn.remote_info['vendor']]
