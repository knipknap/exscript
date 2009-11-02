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
import Exscript.FunctionRunner
from Exscript.FooLib import Interact
from Exscript        import Exscript, Account, Host

def read_login():
    user, password = Interact.get_login()
    return Account(user, password)

def run(users, hosts, func, *data, **kwargs):

    if isinstance(users, Account):
        users = [users]
    if isinstance(hosts, Host):
        hosts = [hosts]

    exscript = Exscript(**kwargs)
    job      = FunctionRunner.FunctionRunner(func, *data, **kwargs)
    for user in users:
        exscript.add_account(user)
    for host in hosts:
        job.add_host(host)
    exscript.run(job)

def quickrun(hosts, func, *data, **kwargs):
    return run(read_login(), hosts, func, *data, **kwargs)
