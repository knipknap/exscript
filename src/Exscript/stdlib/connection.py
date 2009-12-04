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
from Exscript.protocols.Exception import InvalidCommandException

True  = 1
False = 0

def authenticate(scope, user = [None], password = [None]):
    """
    Looks for any username/password prompts on the current connection
    and logs in using the given user and password.
    If a user and password are not given, the function uses the same
    user and password that were used at the last login attempt; it is
    an error if no such attempt was made before.

    @type  user: string
    @param user: A username.
    @type  password: string
    @param password: A password.
    """
    conn = scope.get('__connection__')
    conn.transport.authenticate(user[0], password[0], wait = True)
    return True

def authorize(scope, password = [None]):
    """
    Looks for a password prompt on the current connection
    and enters the given password.
    If a password is not given, the function uses the same
    password that was used at the last login attempt; it is
    an error if no such attempt was made before.

    @type  password: string
    @param password: A password.
    """
    conn = scope.get('__connection__')
    conn.transport.authorize(password[0], wait = True)
    return True

def auto_authorize(scope, password = [None]):
    """
    Executes a command on the remote host that causes an authorization
    procedure to be started, then authorizes using the given password
    in the same way in which authorize() works.
    Depending on the detected operating system of the remote host the
    following commands are started:

      - on IOS, the "enable" command is executed.
      - nothing on other operating systems yet.

    @type  password: string
    @param password: A password.
    """
    scope.get('__connection__').auto_authorize(password = password[0])
    return True

def close(scope):
    """
    Closes the existing connection with the remote host. This function is
    rarely used, as normally Exscript closes the connection automatically
    when the script has completed.
    """
    conn = scope.get('__connection__')
    conn.close(1)
    scope.define(__response__ = conn.response)
    return True

def exec_(scope, data):
    """
    Sends the given data to the remote host and waits until the host
    has responded with a prompt.
    If the given data is a list of strings, each item is sent, and
    after each item a prompt is expected.

    This function also causes the response of the command to be stored
    in the built-in __response__ variable.

    @type  data: string
    @param data: The data that is sent.
    """
    conn     = scope.get('__connection__')
    response = []
    for line in data:
        conn.send(line)
        conn.expect_prompt()
        response += conn.response.split('\n')[1:]
    scope.define(__response__ = response)
    return True

def execline(scope, data):
    """
    Like exec(), but appends a newline to the command in data before sending
    it.

    @type  data: string
    @param data: The data that is sent.
    """
    conn     = scope.get('__connection__')
    response = []
    for line in data:
        conn.execute(line)
        response += conn.response.split('\n')[1:]
    scope.define(__response__ = response)
    return True

def send(scope, data):
    """
    Like exec(), but does not wait for a response of the remote host after
    sending the command.

    @type  data: string
    @param data: The data that is sent.
    """
    conn = scope.get('__connection__')
    for line in data:
        conn.send(line)
    return True

def sendline(scope, data):
    """
    Like execline(), but does not wait for a response of the remote host after
    sending the command.

    @type  data: string
    @param data: The data that is sent.
    """
    conn = scope.get('__connection__')
    for line in data:
        conn.send(line + '\r')
    return True

def wait_for(scope, prompt):
    """
    Waits until the response of the remote host contains the given pattern.

    @type  prompt: regex
    @param prompt: The prompt pattern.
    """
    conn = scope.get('__connection__')
    conn.expect(prompt)
    scope.define(__response__ = conn.response)
    return True

def set_prompt(scope, prompt = None):
    """
    Defines the pattern that is recognized at any future time when Exscript
    needs to wait for a prompt.
    In other words, whenever Exscript waits for a prompt, it searches the
    response of the host for the given pattern and continues as soon as the
    pattern is found.

    Exscript waits for a prompt whenever it sends a command (unless the send()
    method was used). set_prompt() redefines as to what is recognized as a
    prompt.

    @type  prompt: regex
    @param prompt: The prompt pattern.
    """
    conn = scope.get('__connection__')
    conn.set_prompt(prompt)
    return True

def set_error(scope, error_re = None):
    """
    Defines a pattern that, whenever detected in the response of the remote
    host, causes an error to be raised.

    In other words, whenever Exscript waits for a prompt, it searches the
    response of the host for the given pattern and raises an error if the
    pattern is found.

    @type  error_re: regex
    @param error_re: The error pattern.
    """
    conn = scope.get('__connection__')
    conn.set_error(error_re)
    return True

def set_timeout(scope, timeout):
    """
    Defines the time after which Exscript fails if it does not receive a
    prompt from the remote host.

    @type  timeout: int
    @param timeout: The timeout in seconds.
    """
    conn = scope.get('__connection__')
    conn.set_timeout(int(timeout[0]))
    return True
