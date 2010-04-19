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
"""
Utilities for reading data from files.
"""
import re, os, base64
from Exscript import Account, Host

def get_accounts_from_file(filename):
    """
    Reads a list of user/password combinations from the given file
    and creates an Account instance for each of them.
    Returns a list of accounts.

    @type  filename: string
    @param filename: The name of the file containing the list of accounts.
    @rtype:  list[Account]
    @return: The newly created account instances.
    """
    accounts           = []
    cfgparser          = __import__('ConfigParser', {}, {}, [''])
    parser             = cfgparser.RawConfigParser()
    parser.optionxform = str
    parser.read(filename)
    for user, password in parser.items('account-pool'):
        accounts.append(Account(user, base64.decodestring(password)))
    return accounts


def get_hosts_from_file(filename, remove_duplicates = False):
    """
    Reads a list of hostnames from the file with the given name.

    @type  filename: string
    @param filename: A full filename.
    @type  remove_duplicates: bool
    @param remove_duplicates: Whether duplicates are removed.
    @rtype:  list[Host]
    @return: The newly created host instances.
    """
    # Open the file.
    if not os.path.exists(filename):
        raise IOError('No such file: %s' % filename)
    file_handle = open(filename, 'r')

    # Read the hostnames.
    have  = {}
    hosts = []
    for line in file_handle:
        hostname = line.split('#')[0].strip()
        if hostname == '':
            continue
        if remove_duplicates and hostname in have:
            continue
        have[hostname] = 1
        hosts.append(Host(hostname))

    file_handle.close()
    return hosts


def get_hosts_from_csv(filename):
    """
    Reads a list of hostnames and variables from the .csv file with the
    given name.

    @type  filename: string
    @param filename: A full filename.
    @rtype:  list[Host]
    @return: The newly created host instances.
    """
    # Open the file.
    if not os.path.exists(filename):
        raise IOError('No such file: %s' % filename)
    file_handle = open(filename, 'r')

    # Read the header.
    header = file_handle.readline().rstrip()
    if re.search(r'^hostname\b', header) is None:
        msg  = 'Syntax error in CSV file header:'
        msg += ' File does not start with "hostname".'
        raise Exception(msg)
    if re.search(r'^hostname(?:\t[^\t]+)*$', header) is None:
        msg  = 'Syntax error in CSV file header:'
        msg += ' Make sure to separate columns by tabs.'
        raise Exception(msg)
    varnames = header.split('\t')
    varnames.pop(0)

    # Walk through all lines and create a map that maps hostname to
    # definitions.
    last_uri = ''
    line_re  = re.compile(r'[\r\n]*$')
    hosts    = []
    for line in file_handle:
        if line.strip() == '':
            continue

        line   = line_re.sub('', line)
        values = line.split('\t')
        uri    = values.pop(0).strip()

        # Add the hostname to our list.
        if uri != last_uri:
            #print "Reading hostname", hostname_url, "from csv."
            host     = Host(uri)
            last_uri = uri
            hosts.append(host)

        # Define variables according to the definition.
        for i in range(0, len(varnames)):
            try:
                value = values[i]
            except:
                value = ''
            host.append(varnames[i], value)

    file_handle.close()
    return hosts
