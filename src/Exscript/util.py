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
import re, os, base64
from Exscript    import Exscript
from Interpreter import Parser
from FooLib      import Interact
from Account     import Account
from Host        import Host

def _first_match(string, compiled):
    match = compiled.search(string)
    if match is None and compiled.groups <= 1:
        return None
    elif match is None:
        return [None for i in range(0, compiled.groups)]
    elif compiled.groups == 0:
        return string
    elif compiled.groups == 1:
        return match.groups(1)[0]
    else:
        return [match.groups(i)[0] for i in range(1, compiled.groups + 1)]


def first_match(string, regex, flags = re.M):
    return _first_match(string, re.compile(regex, flags))


def any_match(string, regex):
    compiled = re.compile(regex)
    results  = []
    if compiled.groups <= 1:
        for line in string.split('\n'):
            match = _first_match(line, compiled)
            if match is None:
                continue
            results.append(match)
    else:
        for line in string.split('\n'):
            match = _first_match(line, compiled)
            if match[0] is None:
                continue
            results.append(match)
    return results


def read_login():
    user, password = Interact.get_login()
    return Account(user, password)


def run(users, hosts, func, *data, **kwargs):
    from FunctionRunner import FunctionRunner

    if isinstance(users, Account):
        users = [users]
    if isinstance(hosts, Host):
        hosts = [hosts]

    exscript = Exscript(**kwargs)
    job      = FunctionRunner(func, *data, **kwargs)
    for user in users:
        exscript.add_account(user)
    for host in hosts:
        job.add_host(host)
    exscript.run(job)


def quickrun(hosts, func, *data, **kwargs):
    return run(read_login(), hosts, func, *data, **kwargs)


def os_function_mapper(exscript, host, conn, map, *data, **kwargs):
    os   = conn.guess_os()
    func = map.get(os)
    if func is None:
        raise Exception('No handler for %s found.' % os)
    return func(exscript, host, conn, *data, **kwargs)


def get_hosts_from_file(filename):
    """
    Reads a list of hostnames from the file with the given name.

    @type  filename: string
    @param filename: A full filename.
    """
    # Open the file.
    if not os.path.exists(filename):
        raise IOError('No such file: %s' % filename)
    file_handle = open(filename, 'r')

    # Read the hostnames.
    hosts = []
    for line in file_handle:
        hostname = line.strip()
        if hostname == '':
            continue
        hosts.append(Host(hostname))

    file_handle.close()
    return hosts


def get_accounts_from_file(filename):
    """
    Reads a list of user/password combinations from the given file 
    and creates an Account instance for each of them.
    Returns a list of accounts.

    @type  filename: string
    @param filename: The name of the file containing the list of accounts.
    @rtype:  list[Account]
    @return: The newly added account instances.
    """
    accounts  = []
    cfgparser = __import__('ConfigParser', globals(), locals(), [''])
    parser    = cfgparser.RawConfigParser()
    parser.read(filename)
    for user, password in parser.items('account-pool'):
        accounts.append(Account(user, base64.decodestring(password)))
    return accounts


def get_hosts_from_csv(filename):
    """
    Reads a list of hostnames and variables from the .csv file with the 
    given name.

    @type  filename: string
    @param filename: A full filename.
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


def run_template(exscript, conn, template, **kwargs):
    # Define default variables.
    defaults = dict(__filename__ = template,
                    hostname     = conn.get_host())

    # Init the parser and compile the template.
    parser = Parser()
    parser.define(**defaults)
    parser.define(**kwargs)
    compiled = parser.parse_file(template)
    compiled.define(__exscript__   = exscript)
    compiled.define(__connection__ = conn)

    # Run.
    return compiled.execute()
