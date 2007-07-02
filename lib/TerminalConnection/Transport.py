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
        self.on_data_received_cb   = kwargs.get('on_data_received',      None)
        self.on_data_received_args = kwargs.get('on_data_received_args', None)


    def set_on_data_received_cb(self, func, args = None):
        self.on_data_received_cb   = func
        self.on_data_received_args = args


    def set_prompt(self, prompt = None):
        AbstractMethod()


    def set_timeout(self, timeout):
        AbstractMethod()


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
