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
from Exscript.FooLib import Interact
from Exscript        import Exscript, Account, Host

def read_login():
    user, password = Interact.get_login()
    return Account(user, password)

def run(users, hosts, func, *data, **kwargs):
    exscript = Exscript(**kwargs)
    exscript.add_account(users)
    exscript.run(hosts, func, *data, **kwargs)

def quickrun(hosts, func, *data, **kwargs):
    return run(read_login(), hosts, func, *data, **kwargs)
