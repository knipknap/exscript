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
from Exscript       import Exscript
from FooLib         import Interact
from Account        import Account
from Host           import Host
from FunctionRunner import FunctionRunner


def _first_match(string, compiled):
    match = compiled.search(string)
    if match is None and compiled.groups == 0:
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
    n_groups = compiled.groups
    results  = []
    for line in string.split('\n'):
        match = _first_match(line, compiled)
        if match is None:
            continue
        results.append(match)
    return results


def read_login():
    user, password = Interact.get_login()
    return Account(user, password)


def run(users, hosts, func, *data):
    if isinstance(users, Account):
        users = [users]
    if isinstance(hosts, Host):
        hosts = [hosts]

    exscript = Exscript()
    job      = FunctionRunner(func, *data)
    for user in users:
        exscript.add_account(user)
    for host in hosts:
        job.add_host(host)
    exscript.run(job)


def quickrun(hosts, func, *data):
    return run(read_login(), hosts, func, *data)


def os_function_mapper(exscript, host, conn, map, *data):
    os   = conn.guess_os()
    func = map.get(os)
    if func is None:
        raise Exception('No handler for %s found.' % os)
    return func(exscript, host, conn, *data)
