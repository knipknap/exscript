# Copyright (C) 2010 Samuel Abels.
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
import os
from Exscriptd.Config               import Config
from Exscriptd.config.ConfigSection import ConfigSection

class AccountPoolConfig(ConfigSection):
    def __init__(self, *args, **kwargs):
        ConfigSection.__init__(self, *args, **kwargs)
        self.pool_name = None
        self.filename  = None
        self.config    = Config(self.global_options.config_dir, False)

    @staticmethod
    def get_description():
        return 'add or configure account pools'

    @staticmethod
    def get_commands():
        return (('add',  'add a new account pool'),
                ('edit', 'replace an existing account pool'))

    def prepare_add(self, parser, pool_name, filename):
        self.pool_name = pool_name
        self.filename  = filename
        if not os.path.isfile(filename):
            parser.error('invalid file: ' + filename)
        if self.config.has_account_pool(self.pool_name):
            parser.error('account pool already exists')

    def start_add(self):
        self.config.add_account_pool_from_file(self.pool_name, self.filename)
        print 'Account pool added.'

    def prepare_edit(self, parser, pool_name, filename):
        self.pool_name = pool_name
        self.filename  = filename
        if not os.path.isfile(filename):
            parser.error('invalid file: ' + filename)
        if not self.config.has_account_pool(self.pool_name):
            parser.error('account pool not found')

    def start_edit(self):
        self.config.add_account_pool_from_file(self.pool_name, self.filename)
        print 'Account pool configured.'
