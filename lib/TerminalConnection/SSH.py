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
from Transport import Transport as Base
import sys, os, time, re
import pexpect
from Telnet import newline, pass_re, login_fail_re

True  = 1
False = 0

flags     = re.I | re.M
prompt_re = re.compile(r'[\r\n]*\w+[\-\w\(\)\@:~]*[#>%\$]',    flags)


class Transport(Base):
    def __init__(self, *args, **kwargs):
        Base.__init__(self, **kwargs)
        self.conn     = None
        self.debug    = kwargs.get('debug', 0)
        self.prompt   = prompt_re
        self.hostname = None


    def __del__(self):
        self.conn.close(True)


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


    def set_prompt(self, prompt = None):
        if prompt is None:
            self.prompt = prompt_re
        else:
            self.prompt = prompt


    def connect(self, hostname):
        self.hostname = hostname
        return True


    def authenticate(self, user, password):
        self.conn = pexpect.spawn('ssh %s@%s' % (user, self.hostname))
        self.conn.setecho(self.echo)
        self.conn.expect(pass_re)
        self._receive_cb(self.conn.before + self.conn.after)
        self.execute(password)


    def authorize(self, password):
        pass #FIXME: No idea whether AAA is supported via SSH


    def expect_prompt(self):
        try:
            self.conn.expect(self.prompt)
            buf = self.conn.before + self.conn.after
        except pexpect.EOF:
            buf = self.conn.before
        self._receive_cb(buf)
        return buf.split('\n')


    def execute(self, command):
        self.conn.sendline(command)
        return self.expect_prompt()


    def send(self, data):
        self.conn.send(data)


    def close(self):
        self.conn.expect(pexpect.EOF)
        self._receive_cb(self.conn.before)
        self.conn.close()
