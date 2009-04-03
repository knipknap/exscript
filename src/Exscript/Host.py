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
from FooLib import UrlParser

def is_ip(str):
    if re.compile('\d+\.\d+\.\d+\.\d+').match(str):
        return True
    if ':' in str:   # IPv6
        return True
    return False

class Host(object):
    def __init__(self, uri, **kwargs):
        self.protocol = 'telnet'
        self.vars     = kwargs
        self.username = None
        self.password = None
        self.set_uri(uri) 


    def set_uri(self, uri):
        uri = UrlParser.parse_url(uri, self.protocol)
        self.set_protocol(uri.protocol)
        self.set_tcp_port(uri.port)
        self.set_address(uri.hostname)
        self.set_username(uri.username)
        self.set_password(uri.password)

        for key, val in uri.vars.iteritems():
            host.define(key, val)


    def set_address(self, address):
        if '.' in address and not is_ip(address):
            self.address, self.domain = address.split('.')
        else:
            self.address = address
            self.domain  = ''


    def get_address(self):
        """
        Returns the name with the domain appended (if any).
        """
        if self.domain and not '.' in self.address:
            return self.address + '.' + self.domain
        return self.address


    def get_name(self):
        """
        Returns the name, excluding the domain part.
        """
        return self.address


    def set_domain(self, domain):
        self.domain = domain


    def get_domain(self):
        return self.domain


    def set_protocol(self, protocol):
        self.protocol = protocol


    def get_protocol(self):
        return self.protocol


    def set_tcp_port(self, tcp_port):
        self.tcp_port = tcp_port


    def get_tcp_port(self):
        return self.tcp_port


    def set_username(self, name):
        self.username = name


    def get_username(self):
        return self.username


    def set_password(self, password):
        self.password = password


    def get_password(self):
        return self.password


    def set(self, name, value):
        self.vars[var] = value


    def append(self, name, value):
        if self.vars.has_key(name):
            self.vars[var].append(value)
        else:
            self.vars[var] = [value]


    def set_default(self, name, value):
        if not self.vars.has_key(name):
            self.vars[name] = value


    def has_key(self, name):
        return self.vars.has_key(name)


    def get(self, name, default = None):
        return self.vars.get(name, default)
