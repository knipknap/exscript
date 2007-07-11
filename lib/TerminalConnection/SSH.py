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
import os, time

class Transport(Base):
    def __init__(self, *args, **kwargs):
        Base.__init__(self, **kwargs)
        self.pid    = None
        self.fd     = None
        self.debug  = kwargs.get('debug', 0)
        self.prompt = prompt_re


    def connect(self, hostname):
        #FIXME


    def authenticate(self, user, password):
        #FIXME


    def authorize(self, password):
        #FIXME


    def expect_prompt(self):
        #FIXME


    def execute(self, command):
        #FIXME


    def send(self, data):
        #FIXME


    def close(self):
        #FIXME
