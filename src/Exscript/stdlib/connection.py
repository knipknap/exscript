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
from termconnect.Exception import InvalidCommandException

True  = 1
False = 0

def authenticate(scope, user = [None], password = [None]):
    conn = scope.get('__connection__')
    conn.transport.authenticate(user[0], password[0], wait = True)
    return True

def authorize(scope, password = [None]):
    conn = scope.get('__connection__')
    conn.transport.authorize(password[0], wait = True)
    return True

def auto_authorize(scope, password = [None]):
    scope.get('__connection__').auto_authorize(password = password[0])
    return True

def close(scope):
    conn = scope.get('__connection__')
    conn.close(1)
    scope.define(_buffer = conn.response)
    return True

def exec_(scope, data):
    conn     = scope.get('__connection__')
    response = []
    for line in data:
        conn.send(line)
        conn.expect_prompt()
        response += conn.response.split('\n')[1:]
    scope.define(_buffer = response)
    return True

def execline(scope, data):
    conn     = scope.get('__connection__')
    response = []
    for line in data:
        conn.execute(line)
        response += conn.response.split('\n')[1:]
    scope.define(_buffer = response)
    return True

def send(scope, data, wait = None):
    conn = scope.get('__connection__')
    for line in data:
        conn.send(line)
    return True

def sendline(scope, data):
    conn = scope.get('__connection__')
    for line in data:
        conn.send(line + '\r')
    return True

def set_error(scope, error_re = None):
    conn = scope.get('__connection__')
    conn.set_error(error_re)
    return True

def set_prompt(scope, prompt = None):
    conn = scope.get('__connection__')
    conn.set_prompt(prompt)
    return True

def set_timeout(scope, timeout):
    conn = scope.get('__connection__')
    conn.set_timeout(int(timeout[0]))
    return True

def wait_for(scope, prompt):
    conn = scope.get('__connection__')
    conn.expect(prompt)
    scope.define(_buffer = conn.response)
    return True
