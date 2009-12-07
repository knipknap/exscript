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
from util.ipv4 import is_ip as is_ipv4_ip
from util.url  import parse_url

def is_ip(string):
    # Adds IPv6 support.
    return ':' in string or is_ipv4_ip(string)

class Host(object):
    """
    Represents a device on which to open a connection.
    """

    def __init__(self, uri, **kwargs):
        """
        Constructor. The given uri is passed to Host.set_uri(). The given
        kwargs are variables that are passed to Host.set().

        @type  uri: string
        @param uri: A hostname; see set_uri() for more info.
        @type  kwargs: dict
        @param kwargs: Variables to define using Host.set()
        """
        self.protocol = 'telnet'
        self.vars     = kwargs
        self.username = None
        self.password = None
        self.set_uri(uri) 


    def set_uri(self, uri):
        """
        Defines the protocol, hostname, domain, TCP port number, username,
        and password from the given URL. The hostname may be URL formatted,
        so the following formats are all valid:

            - myhostname
            - myhostname.domain
            - ssh:hostname
            - ssh:hostname.domain
            - ssh://hostname
            - ssh://user@hostname
            - ssh://user:password@hostname
            - ssh://user:password@hostname:21

        For a list of supported protocols please see set_protocol().

        @type  uri: string
        @param uri: An URL formatted hostname.
        """
        uri      = parse_url(uri, self.protocol)
        hostname = uri.hostname or ''
        address  = uri.path and hostname + uri.path or hostname
        self.set_protocol(uri.protocol)
        self.set_tcp_port(uri.port)
        self.set_address(address)
        self.set_username(uri.username)
        self.set_password(uri.password)

        for key, val in uri.vars.iteritems():
            self.append(key, val)


    def set_address(self, address):
        """
        Set the hostname/domain or IP address of the remote host without
        changing username, password, protocol, and TCP port number.

        @type  address: string
        @param address: A hostname or IP address.
        """
        if '.' in address and not is_ip(address):
            self.address, self.domain = address.split('.', 1)
        else:
            self.address = address
            self.domain  = ''


    def get_address(self):
        """
        Returns the name with the domain appended (if any).

        @rtype:  string
        @return: The hostname including the domain name.
        """
        if self.domain and not '.' in self.address:
            return self.address + '.' + self.domain
        return self.address


    def set_name(self, name):
        """
        Defines the hostname, without changing the domain.

        @type  name: string
        @param name: A hostname or IP address.
        """
        self.address = name


    def get_name(self):
        """
        Returns the hostname, excluding the domain part.

        @rtype:  string
        @return: The hostname excluding the domain name.
        """
        return self.address


    def set_domain(self, domain):
        """
        Defines the domain name.

        @type  domain: string
        @param domain: A domain name, or None for default.
        """
        self.domain = domain


    def get_domain(self):
        """
        Returns the domain name.

        @rtype:  string
        @return: The domain name.
        """
        return self.domain


    def set_protocol(self, protocol):
        """
        Defines the protocol. The following protocols are currently
        supported:

            - telnet: Telnet
            - ssh1: SSH version 1
            - ssh2: SSH version 2
            - ssh: Automatically selects the best supported SSH version
            - dummy: A virtual device that accepts any command, but that
              does not respond anything useful.
            - pseudo: A virtual device that loads a file with the given
              "hostname". The given file is a Python file containing
              information on how the virtual device shall respond to
              commands. For more information please refer to the
              documentation of
              protocols.Dummy.load_command_handler_from_file().

        @type  protocol: string
        @param protocol: The protocol name.
        """
        self.protocol = protocol


    def get_protocol(self):
        """
        Returns the name of the protocol.

        @rtype:  string
        @return: The protocol name.
        """
        return self.protocol


    def set_tcp_port(self, tcp_port):
        """
        Defines the TCP port number.

        @type  tcp_port: int
        @param tcp_port: The TCP port number.
        """
        self.tcp_port = tcp_port


    def get_tcp_port(self):
        """
        Returns the TCP port number.

        @rtype:  string
        @return: The TCP port number.
        """
        return self.tcp_port


    def set_username(self, name):
        """
        Defines the username of the account that is used to log in.

        @type  name: string
        @param name: The username.
        """
        self.username = name


    def get_username(self):
        """
        Returns the username of the account that is used to log in.

        @rtype:  string
        @return: The username.
        """
        return self.username


    def set_password(self, password):
        """
        Defines the password of the account that is used to log in.

        @type  password: string
        @param password: The password.
        """
        self.password = password


    def get_password(self):
        """
        Returns the password of the account that is used to log in.

        @rtype:  string
        @return: The password.
        """
        return self.password


    def set(self, name, value):
        """
        Stores the given variable/value in the object for later retrieval.

        @type  name: string
        @param name: The name of the variable.
        @type  value: object
        @param value: The value of the variable.
        """
        self.vars[name] = value


    def append(self, name, value):
        """
        Appends the given value to the list variable with the given name.

        @type  name: string
        @param name: The name of the variable.
        @type  value: object
        @param value: The appended value.
        """
        if self.vars.has_key(name):
            self.vars[name].append(value)
        else:
            self.vars[name] = [value]


    def set_default(self, name, value):
        """
        Like set(), but only sets the value if the variable is not already
        defined.

        @type  name: string
        @param name: The name of the variable.
        @type  value: object
        @param value: The value of the variable.
        """
        if not self.vars.has_key(name):
            self.vars[name] = value


    def has_key(self, name):
        """
        Returns True if the variable with the given name is defined, False
        otherwise.

        @type  name: string
        @param name: The name of the variable.
        @rtype:  bool
        @return: Whether the variable is defined.
        """
        return self.vars.has_key(name)


    def get(self, name, default = None):
        """
        Returns the value of the given variable, or the given default
        value if the variable is not defined.

        @type  name: string
        @param name: The name of the variable.
        @type  default: object
        @param default: The default value.
        @rtype:  object
        @return: The value of the variable.
        """
        return self.vars.get(name, default)
