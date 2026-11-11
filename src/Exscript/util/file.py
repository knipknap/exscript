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
Utilities for reading data from files.
"""

import base64
import binascii
import configparser
import importlib.machinery
import importlib.util
import os
import re
from typing import Any, cast

from .. import Account, Host
from .cast import to_host


def get_accounts_from_file(
    filename: str | os.PathLike[str], encoding: str = 'utf-8', password_encoding: str = 'utf-8'
) -> list[Account]:
    """
    Reads a list of user/password combinations from the given file
    and returns a list of Account instances. The file content
    has the following format::

        [account-pool]
        user1 = cGFzc3dvcmQ=
        user2 = cGFzc3dvcmQ=

    Note that "cGFzc3dvcmQ=" is a base64 encoded password.
    If the input file contains extra config sections other than
    "account-pool", they are ignored.
    Each password needs to be base64 encoded. Base64 does not protect the
    passwords: anyone who can read the file can decode them. To encode a
    password, you may use the following command::

        python3 -c 'import base64; print(base64.b64encode("thepassword".encode()).decode())'

    Raises OSError if the file cannot be opened, e.g. FileNotFoundError if
    it does not exist, binascii.Error if a password is not valid base64, and
    ValueError if it is not valid in the password encoding. Their messages
    name the user, but not the password.

    :type  filename: str|os.PathLike
    :param filename: The name of the file containing the list of accounts.
    :type  encoding: str
    :param encoding: The encoding of the file.
    :type  password_encoding: str
    :param password_encoding: The encoding of the original passwords.
    :rtype:  list[Account]
    :return: The newly created account instances.
    """
    accounts: list[Account] = []
    parser = configparser.RawConfigParser()
    # str keeps the case of the user names. The stub declares optionxform as
    # a method, which may not be replaced; the cast is for the type checker.
    cast(Any, parser).optionxform = str
    with open(filename, encoding=encoding) as fp:  # read() skips files it cannot open
        parser.read_file(fp)
    for user, password in parser.items('account-pool'):
        # The errors of the decoders show parts of the password: not chained.
        try:
            data = base64.decodebytes(password.encode('ascii'))
        except (UnicodeEncodeError, binascii.Error):
            msg = 'Could not decode password for user: %s (invalid base64)' % user
            raise binascii.Error(msg) from None
        try:
            text = data.decode(password_encoding)
        except UnicodeDecodeError:
            msg = 'Could not decode password for user: %s (invalid %s)' % (user, password_encoding)
            raise ValueError(msg) from None
        accounts.append(Account(user, text))
    return accounts


def get_hosts_from_file(
    filename: str | os.PathLike[str],
    default_protocol: str = 'ssh',
    default_domain: str = '',
    remove_duplicates: bool = False,
    encoding: str = 'utf-8',
) -> list[Host]:
    """
    Reads a list of hostnames from the file with the given name.
    The file contains one hostname per line, which may be URL formatted
    (see :meth:`Exscript.host.Host.set_uri`). Empty lines and everything after
    a ``#`` are ignored. Raises OSError if the file does not exist.

    :type  filename: str|os.PathLike
    :param filename: A full filename.
    :type  default_protocol: str
    :param default_protocol: Passed to the Host constructor.
    :type  default_domain: str
    :param default_domain: Appended to each hostname that has no domain.
    :type  remove_duplicates: bool
    :param remove_duplicates: Whether duplicates are removed.
    :type  encoding: str
    :param encoding: The encoding of the file.
    :rtype:  list[Host]
    :return: The newly created host instances.
    """
    # Open the file.
    if not os.path.exists(filename):
        raise OSError('No such file: %s' % filename)

    # Read the hostnames.
    have: set[str] = set()
    hosts: list[Host] = []
    with open(filename, encoding=encoding) as file_handle:
        for line in file_handle:
            hostname = line.split('#')[0].strip()
            if hostname == '':
                continue
            if remove_duplicates and hostname in have:
                continue
            have.add(hostname)
            hosts.append(to_host(hostname, default_protocol, default_domain))

    return hosts


def get_hosts_from_csv(
    filename: str | os.PathLike[str],
    default_protocol: str = 'ssh',
    default_domain: str = '',
    encoding: str = 'utf-8',
) -> list[Host]:
    """
    Reads a list of hostnames and variables from the tab-separated .csv file
    with the given name. The first line of the file must contain the column
    names, e.g.::

        address	testvar1	testvar2
        10.0.0.1	value1	othervalue
        10.0.0.1	value2	othervalue2
        10.0.0.2	foo	bar

    For the above example, the function returns *two* host objects, where
    the 'testvar1' variable of the first host holds a list containing two
    entries ('value1' and 'value2'), and the 'testvar1' variable of the
    second host contains a list with a single entry ('foo').

    Both, the address and the hostname of each host are set to the address
    given in the first column. If you want the hostname set to another value,
    you may add a second column containing the hostname::

        address	hostname	testvar
        10.0.0.1	myhost	value
        10.0.0.2	otherhost	othervalue

    :type  filename: str|os.PathLike
    :param filename: A full filename.
    :type  default_protocol: str
    :param default_protocol: Passed to the Host constructor.
    :type  default_domain: str
    :param default_domain: Appended to each hostname that has no domain.
    :type  encoding: str
    :param encoding: The encoding of the file.
    :rtype:  list[Host]
    :return: The newly created host instances.
    """
    # Open the file.
    if not os.path.exists(filename):
        raise OSError('No such file: %s' % filename)

    with open(filename, encoding=encoding) as file_handle:
        # Read and check the header.
        header = file_handle.readline().rstrip()
        if re.search(r'^(?:hostname|address)\b', header) is None:
            msg = 'Syntax error in CSV file header:'
            msg += ' File does not start with "hostname" or "address".'
            raise Exception(msg)
        if re.search(r'^(?:hostname|address)(?:\t[^\t]+)*$', header) is None:
            msg = 'Syntax error in CSV file header:'
            msg += ' Make sure to separate columns by tabs.'
            raise Exception(msg)
        varnames = [str(v) for v in header.split('\t')]
        varnames.pop(0)

        # Walk through all lines and create a map that maps hostname to
        # definitions.
        last_uri = ''
        line_re = re.compile(r'[\r\n]*$')
        hosts: list[Host] = []
        for line in file_handle:
            if line.strip() == '':
                continue

            line = line_re.sub('', line)
            values = line.split('\t')
            uri = values.pop(0).strip()

            # Add the hostname to our list.
            if uri != last_uri:
                # print "Reading hostname", hostname_url, "from csv."
                host = to_host(uri, default_protocol, default_domain)
                last_uri = uri
                hosts.append(host)

            # Define variables according to the definition.
            for i, varname in enumerate(varnames):
                try:
                    value = values[i]
                except IndexError:
                    value = ''
                if varname == 'hostname':
                    host.set_name(value)
                else:
                    host.append(varname, value)

    return hosts


# Any: the values are the objects in the __lib__ variable of the loaded file,
# which are not checked.
def load_lib(filename: str) -> dict[str, Any]:
    """
    Loads a Python file containing functions, and returns the
    content of the __lib__ variable. The __lib__ variable must contain
    a dictionary mapping function names to callables.

    Returns a dictionary mapping the namespaced function names to
    callables. The namespace is the basename of the file, without file
    extension. Raises OSError if the file does not exist.

    :type  filename: string
    :param filename: A full filename.
    :rtype:  dict[string->object]
    :return: The loaded functions.
    """
    # Open the file.
    if not os.path.exists(filename):
        raise OSError('No such file: %s' % filename)

    name = os.path.splitext(os.path.basename(filename))[0]
    # load_module() was removed in Python 3.15; an explicit loader also accepts other suffixes.
    loader = importlib.machinery.SourceFileLoader(name, filename)
    spec = importlib.util.spec_from_file_location(name, filename, loader=loader)
    # With a loader given, spec_from_file_location() does not return None.
    module = importlib.util.module_from_spec(cast(importlib.machinery.ModuleSpec, spec))
    loader.exec_module(module)

    return dict((name + '.' + k, v) for (k, v) in list(module.__lib__.items()))
