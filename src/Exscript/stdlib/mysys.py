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
import time

True  = 1
False = 0

def message(scope, string):
    exscript = scope.get('__connection__').get_exscript()
    exscript._print(string[0] + '\n')
    return True

def tacacs_lock(scope, user):
    accm    = scope.get('__connection__').get_account_manager()
    account = accm.get_account_from_name(user[0])
    accm.acquire_account(account)
    return True

def tacacs_unlock(scope, user):
    accm    = scope.get('__connection__').get_account_manager()
    account = accm.get_account_from_name(user[0])
    account.release()
    return True

def wait(scope, seconds):
    time.sleep(int(seconds[0]))
    return True
