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
import string, re, sys
from AbstractMethod import AbstractMethod
from Exception      import TransportException, InvalidCommandException

True  = 1 
False = 0 

flags         = re.I | re.M
printable     = re.escape(string.printable)
ignore        = r'[\x1b\x07\x00]'
newline       = r'[\r\n]'
prompt_start  = r'(?:' + newline + r'[^' + printable + r']?|' + ignore + '+)'
prompt_chars  = r'[\-\w\(\)@:~]'
filename      = r'(?:[\w\+\-\._]+)'
path          = r'(?:(?:' + filename + r')?(?:/' + filename + r')*/?)'
any_path      = r'(?:' + path + r'|~' + path + r'?)'
host          = r'(?:[\w+\-\.]+)'
user          = r'(?:[\w+\-]+)'
user_host     = r'(?:(?:' + user + r'\@)?' + host + r')'
prompt_re     = re.compile(prompt_start                 \
                         + r'[\[\<]?'                   \
                         + r'\w+'                       \
                         + user_host + r'?'             \
                         + r'[: ]?'                     \
                         + any_path + r'?'              \
                         + r'[: ]?'                     \
                         + any_path + r'?'              \
                         + r'(?:\(' + filename + '\))?' \
                         + r'\]?'                       \
                         + r'[#>%\$\]] ?$', flags)
iosxr_prompt_re = re.compile(r'RP/\d+/\w+/CPU\d+:[^#]+[#>] ?$', flags)

huawei_re     = re.compile(r'huawei',               flags)
cisco_user_re = re.compile(r'user ?name: *$',       flags)
junos_user_re = re.compile(newline + r'login: *?$', flags)
unix_user_re  = re.compile(r'(user|login): *$',     flags)
pass_re       = re.compile(r'password:? *$',        flags)
skey_re       = re.compile(r'(?:s\/key|otp-md4) (\d+) (\S+)')
errors        = [r'error',
                 r'invalid',
                 r'incomplete',
                 r'unrecognized',
                 r'unknown command',
                 r'connection timed out',
                 r'[^\r\n]+ not found']
error_re      = re.compile(r'^%?\s*(?:' + '|'.join(errors) + r')', flags)
login_fail    = [r'bad secrets',
                 r'denied',
                 r'invalid',
                 r'too short',
                 r'incorrect',
                 r'connection timed out',
                 r'failed']
login_fail_re = re.compile(newline      \
                         + r'[^\r\n]*'  \
                         + r'(?:' + '|'.join(login_fail) + r')', flags)

# Test the prompt types. FIXME: Move into a unit test.
prompts = [r'[sam123@home ~]$',
           r'[MyHost-A1]',
           r'<MyHost-A1>',
           r'sam@knip:~/Code/exscript$',
           r'sam@MyHost-X123>',
           r'sam@MyHost-X123#',
           r'MyHost-ABC-CDE123>',
           r'MyHost-A1#',
           r'S-ABC#',
           r'0123456-1-1-abc#',
           r'0123456-1-1-a>',
           r'MyHost-A1(config)#',
           r'MyHost-A1(config)>',
           r'RP/0/RP0/CPU0:A-BC2#',
           r'FA/0/1/2/3>',
           r'FA/0/1/2/3(config)>',
           r'FA/0/1/2/3(config)#',
           r'admin@s-x-a6.a.bc.de.fg:/# ',
           r'admin@s-x-a6.a.bc.de.fg:/% ']
for prompt in prompts:
    if not prompt_re.search('\n' + prompt):
        raise Exception("Prompt %s does not match exactly." % prompt)
    if not prompt_re.search('this is a test\r\n' + prompt):
        raise Exception("Prompt %s does not match." % prompt)
    if prompt_re.search('some text ' + prompt):
        raise Exception("Prompt %s matches incorrectly." % prompt)

class Transport(object):
    """
    This is the base class for all protocols; it defines the common portions 
    of the API.
    """

    def __init__(self, **kwargs):
        """
        Constructor. kwargs may include:

          - echo: Whether to echo the device response to the terminal. The 
          default is False.
          - debug: An integer between 0 (no debugging) and 5 (very verbose 
          debugging) that specifies the amount of debug info sent to the 
          terminal. The default value is 0.
          - timeout: See set_timeout(). The default value is 30.
          - logfile: A file into which a log of the conversation with the 
          device is dumped.
          - on_data_received: See set_on_data_received_cb().
          - on_data_received_args: The *args argument for 
          set_on_data_received_cb().
          - on_otp_requested: See set_on_otp_requested_cb().
          - on_otp_requested_args: The *args argument for 
          set_on_otp_requested_cb().
        """
        self.prompt_re             = prompt_re
        self.error_re              = error_re
        self.host                  = kwargs.get('host',     None)
        self.user                  = kwargs.get('user',     '')
        self.password              = kwargs.get('password', '')
        self.echo                  = kwargs.get('echo',     0)
        self.debug                 = kwargs.get('debug',    0)
        self.timeout               = kwargs.get('timeout',  30)
        self.logfile               = kwargs.get('logfile',  None)
        self.log                   = None
        self.on_data_received_cb   = kwargs.get('on_data_received',      None)
        self.on_data_received_args = kwargs.get('on_data_received_args', ())
        self.on_otp_requested      = kwargs.get('on_otp_requested',      None)
        self.on_otp_requested_args = kwargs.get('on_otp_requested_args', ())
        self.last_tacacs_key_id    = None
        self.response              = None
        self.remote_os             = 'unknown'
        if self.logfile is not None:
            self.log = open(kwargs['logfile'], 'a')


    def __copy__(self):
        """
        Overwritten to return the very same object instead of copying the
        stream, because copying a network connection is impossible.

        @rtype:  Transport
        @return: self
        """
        return self


    def __deepcopy__(self, memo):
        """
        Overwritten to return the very same object instead of copying the
        stream, because copying a network connection is impossible.

        @type  memo: object
        @param memo: Please refer to Python's standard library documentation.
        @rtype:  Transport
        @return: self
        """
        return self


    def _receive_cb(self, data, **kwargs):
        data = data.replace(chr(13) + chr(0), '')
        text = data.replace('\r', '')
        if self.echo:
            sys.stdout.write(text)
            sys.stdout.flush()
        if self.log is not None:
            self.log.write(text)
        if self.on_data_received_cb is not None:
            self.on_data_received_cb(data, *self.on_data_received_args)
        return data


    def is_dummy(self):
        """
        Returns True if the adapter implements a virtual device, i.e.
        it isn't an actual network connection.

        @rtype:  Boolean
        @return: True for dummy adapters, False for network adapters.
        """
        return False


    def set_on_data_received_cb(self, func, *args):
        """
        Defines a function that is called whenever data was received from the 
        remote host. The function is passed the following arguments:

          - The data that was retrieved.
          - Any additional arguments passed to set_on_data_received_cb().

        @type  func: object
        @param func: The function that is called.
        @type  args: list
        @param args: Any additional arguments, passed to func().
        """
        self.on_data_received_cb   = func
        self.on_data_received_args = args


    def _otp_cb(self, seq, seed):
        if self.on_otp_requested is not None:
            self.on_otp_requested(seq, seed, *self.on_otp_requested_args)


    def set_on_otp_requested_cb(self, func, *args):
        """
        Defines a function that is called whenever the remote host
        requested that a one time password is entered.
        The function is passed the following arguments:

          - The key number that was requested.
          - The seed (cryptographic salt) that was requested.
          - Any additional arguments passed to set_on_data_received_cb().

        @type  func: object
        @param func: The function that is called.
        @type  args: list
        @param args: Any additional arguments, passed to func().
        """
        self.on_otp_requested      = func
        self.on_otp_requested_args = args


    def _dbg(self, level, msg):
        if self.debug < level:
            return
        print msg


    def set_prompt(self, prompt = None):
        """
        Defines a pattern that is waited for when calling the expect_prompt() 
        method.
        If the set_prompt() method is not called, or if it is called with the 
        prompt argument set to None, a default prompt is used that should 
        work with many devices running Unix, IOS, IOS-XR, or Junos and others.

        @type  prompt: RegEx
        @param prompt: The pattern that matches the prompt of the remote host.
        """
        if prompt is None:
            self.prompt_re = prompt_re
        else:
            self.prompt_re = prompt


    def get_prompt(self):
        """
        Returns the regular expression that is matched against the host
        response when calling the expect_prompt() method.

        @rtype:  regex
        @return: A regular expression.
        """
        return self.prompt_re


    def set_error_prompt(self, error = None):
        """
        Defines a pattern that is used to monitor the response of the
        connected host. If the pattern matches (any time the expect() or
        expect_prompt() methods are used), an error is raised.

        @type  error: RegEx
        @param error: The pattern that, when matched, causes an error.
        """
        if error is None:
            self.error_re = error_re
        else:
            self.error_re = error


    def get_error_prompt(self):
        """
        Returns the regular expression that is used to monitor the response
        of the connected host for errors.

        @rtype:  regex
        @return: A regular expression.
        """
        return self.error_re


    def set_timeout(self, timeout):
        """
        Defines the maximum time that the adapter waits before a call to 
        expect() or expect_prompt() fails.

        @type  timeout: int
        @param timeout: The maximum time in seconds.
        """
        self.timeout = int(timeout)


    def get_timeout(self):
        """
        Returns the current timeout in seconds.

        @rtype:  int
        @return: The timeout in seconds.
        """
        return self.timeout


    def connect(self, hostname = None, port = None):
        """
        Opens the connection to the remote host or IP address.

        @type  hostname: string
        @param hostname: The remote host or IP address.
        @type  port: int
        @param port: The remote TCP port number.
        """
        if hostname is not None:
            self.host = hostname
        return self._connect_hook(self.host, port)


    def authenticate(self, user = None, password = None, **kwargs):
        """
        Authenticates at the remote host. Attempts to smartly recognize the 
        user and password prompts; the following remote operating systems 
        should be supported: Unix, IOS, IOS-XR, JunOS.

        @type  user: string
        @param user: The remote username.
        @type  password: string
        @param password: The plain password.
        @type  kwargs: dict
        @param kwargs: The following arguments are supported:
            - wait: Whether to wait for a prompt using expect_prompt().
        """
        if user is None:
            user = self.user
        if password is None:
            password = self.password
        if user is None:
            raise TypeError('A username is required')
        if password is None:
            raise TypeError('A password is required')
        self.user     = user
        self.password = password

        self._dbg(1, "Attempting to authenticate %s." % user)
        self._authenticate_hook(user, password, **kwargs)


    def authorize(self, password = None, **kwargs):
        """
        Authorizes at the remote host, if the remote host supports 
        authorization. Does nothing otherwise.

        For the difference between authentication and authorization 
        please google for AAA.

        @type  password: string
        @param password: The plain password.
        @type  kwargs: dict
        @param kwargs: The following arguments are supported:
            - wait: Whether to wait for a prompt using expect_prompt().
        """
        if password is None:
            password = self.password
        if password is None:
            raise TypeError('A password is required')
        self.password = password

        self._dbg(1, "Attempting to authorize.")
        self._authorize_hook(password, **kwargs)


    def send(self, data):
        """
        Sends the given data to the remote host.
        Returns without waiting for a response.

        @type  data: string
        @param data: The data that is sent to the remote host.
        @rtype:  Boolean
        @return: True on success, False otherwise.
        """
        AbstractMethod()


    def execute(self, command):
        """
        Sends the given data to the remote host (with a newline appended) 
        and waits for a prompt in the response. The prompt attempts to use 
        a sane default that works with many devices running Unix, IOS, 
        IOS-XR, or Junos and others. If that fails, a custom prompt may 
        also be defined using the set_prompt() method.
        This method also modifies the value of the response (self.response) 
        attribute, for details please see the documentation of the 
        expect() method.

        @type  command: string
        @param command: The data that is sent to the remote host.
        """
        AbstractMethod()


    def expect(self, prompt):
        """
        Monitors the data received from the remote host and waits until 
        the response matches the given prompt. Raises a TransportException 
        on an error (such as a timeout).

        This method also stores the received data in the response 
        attribute (self.response).

        @type  prompt: RegEx
        @param prompt: A regular expression.
        """
        AbstractMethod()


    def expect_prompt(self):
        """
        Monitors the data received from the remote host and waits for a 
        prompt in the response. The prompt attempts to use 
        a sane default that works with many devices running Unix, IOS, 
        IOS-XR, or Junos and others. If that fails, a custom prompt may 
        also be defined using the set_prompt() method.
        This method also stores the received data in the response 
        attribute (self.response).
        """
        self.expect(self.prompt_re)

        # We skip the first line because it contains the echo of the command
        # sent.
        self._dbg(5, "Checking %s for errors" % repr(self.response))
        for line in self.response.split('\n')[1:]:
            match = self.error_re.match(line)
            if match is None:
                continue
            error = repr(self.error_re.pattern)
            self._dbg(5, "error prompt (%s) matches %s" % (error, repr(line)))
            raise InvalidCommandException('Device said:\n' + self.response)


    def close(self, force = False):
        """
        Closes the connection with the remote host.
        """
        AbstractMethod()


    def get_host(self):
        """
        Returns the name or address of the currently connected host.

        @rtype:  string
        @return: A name or an address.
        """
        return self.host


    def guess_os(self):
        """
        Returns an identifer that specifies the operating system that is 
        running on the remote host. This OS is obtained by watching the 
        response of the remote host, such as any messages retrieved during 
        the login procedure.

        The OS is also a wild guess that often depends on volatile 
        information, so there is no guarantee that this will always work.

        @rtype:  string
        @return: A string to help identify the remote operating system.
        """
        return self.remote_os
