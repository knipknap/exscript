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
from AbstractMethod import AbstractMethod

class Transport(object):
    def __init__(self, *args, **kwargs):
        self.prompt                = None
        self.host_type             = 'unknown'
        self.echo                  = kwargs.get('echo',    0)
        self.timeout               = kwargs.get('timeout', 30)
        self.logfile               = kwargs.get('logfile', None)
        self.log                   = None
        self.on_data_received_cb   = kwargs.get('on_data_received',      None)
        self.on_data_received_args = kwargs.get('on_data_received_args', None)
        if self.logfile is not None:
            self.log = open(kwargs['logfile'], 'a')


    def __del__(self):
        if self.log is not None:
            self.log.close()


    def set_on_data_received_cb(self, func, args = None):
        self.on_data_received_cb   = func
        self.on_data_received_args = args


    def set_prompt(self, prompt = None):
        if prompt is None:
            self.prompt = prompt_re
        else:
            self.prompt = prompt


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
