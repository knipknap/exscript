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

flags         = re.I | re.M
printable     = re.escape(string.printable)
ignore        = r'[\x1b\x07]'
newline       = r'[\r\n]'
prompt_start  = r'(?:' + newline + r'[^' + printable + r']?|' + ignore + '+)'
prompt_chars  = r'[\-\w\(\)@:~]'
filename      = r'(?:[\w+\-\._]+)'
path          = r'(?:(?:' + filename + r')?(?:/' + filename + r')*/?)'
any_path      = r'(?:' + path + r'|~' + path + r'?)'
host          = r'(?:[\w+\-\.]+)'
user          = r'(?:[\w+\-]+)'
user_host     = r'(?:(?:' + user + r'\@)?' + host + r')'
prompt_re     = re.compile(prompt_start                 \
                         + r'\[?'                       \
                         + r'\w+'                       \
                         + user_host + r'?'             \
                         + r'[: ]?'                     \
                         + any_path + r'?'              \
                         + r'(?:\(' + filename + '\))?' \
                         + r'\]?'                       \
                         + r'[#>%\$] ?$', flags)

cisco_user_re = re.compile(newline + r'username:', flags)
junos_user_re = re.compile(newline + r'login:',    flags)
unix_user_re  = re.compile(r'(user|login): ?$',    flags)
pass_re       = re.compile(r'password:?',          flags)
skey_re       = re.compile(r'(?:s\/key|otp-md4) (\d+) (\S+)')
error_re      = re.compile(r'^%? ?(?:error|invalid|incomplete)', re.I)
login_fail_re = re.compile(newline + r'[^\r\n]*(?:incorrect|failed|denied)', flags)

# Test the prompt types. FIXME: Move into a unit test.
prompts = [r'[sam123@home ~]$',
           r'sam@knip:~/Code/exscript$',
           r'sam@MyHost-X123>',
           r'sam@MyHost-X123#',
           r'MyHost-ABC-CDE123>',
           r'MyHost-A1#',
           r'0123456-1-1-abc#',
           r'0123456-1-1-a>',
           r'MyHost-A1(config)#',
           r'MyHost-A1(config)>',
           r'FA/0/1/2/3>',
           r'FA/0/1/2/3(config)>',
           r'FA/0/1/2/3(config)#',
           r'admin@s-x-a6.a.bc.de.fg:/#']
for prompt in prompts:
    if not prompt_re.search('\n' + prompt):
        raise Exception("Prompt %s does not match exactly." % prompt)
    if not prompt_re.search('this is a test\r\n' + prompt):
        raise Exception("Prompt %s does not match." % prompt)
    if prompt_re.search('some text ' + prompt):
        raise Exception("Prompt %s matches incorrectly." % prompt)

class Transport(object):
    def __init__(self, *args, **kwargs):
        self.prompt_re             = prompt_re
        self.error_re              = error_re
        self.host_type             = 'unknown'
        self.echo                  = kwargs.get('echo',    0)
        self.timeout               = kwargs.get('timeout', 10)
        self.logfile               = kwargs.get('logfile', None)
        self.log                   = None
        self.on_data_received_cb   = kwargs.get('on_data_received',      None)
        self.on_data_received_args = kwargs.get('on_data_received_args', None)
        self.response              = None
        if self.logfile is not None:
            self.log = open(kwargs['logfile'], 'a')


    def _receive_cb(self, data, **kwargs):
        text = data.replace('\r', '')
        if self.echo:
            sys.stdout.write(text)
            sys.stdout.flush()
        if self.log is not None:
            self.log.write(text)
        if self.on_data_received_cb is not None:
            self.on_data_received_cb(data, self.on_data_received_args)
        return data


    def set_on_data_received_cb(self, func, args = None):
        self.on_data_received_cb   = func
        self.on_data_received_args = args


    def set_prompt(self, prompt = None):
        if prompt is None:
            self.prompt_re = prompt_re
        else:
            self.prompt_re = prompt


    def set_timeout(self, timeout):
        self.timeout = timeout


    def connect(self, hostname):
        AbstractMethod()


    def authenticate(self, user, password):
        AbstractMethod()


    def authorize(self, password):
        AbstractMethod()


    def expect_prompt(self):
        AbstractMethod()


    def execute(self, command):
        AbstractMethod()


    def send(self, data):
        AbstractMethod()


    def close(self):
        AbstractMethod()
