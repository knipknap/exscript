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
from Exscriptd.Config               import Config
from Exscriptd.config.ConfigSection import ConfigSection

class DatabaseConfig(ConfigSection):
    def __init__(self, *args, **kwargs):
        ConfigSection.__init__(self, *args, **kwargs)
        self.db_name = None
        self.dbn     = None
        self.config  = Config(self.global_options.config_dir, False)

    @staticmethod
    def get_description():
        return 'add, edit, or remove databases'

    @staticmethod
    def get_commands():
        return (('add',  'configure a new database'),
                ('edit', 'configure an existing database'))

    def prepare_add(self, parser, db_name, dbn):
        self.db_name = db_name
        self.dbn     = dbn
        if self.config.has_database(self.db_name):
            parser.error('database already exists')

    def start_add(self):
        self.config.add_database(self.db_name, self.dbn)
        print 'Database added.'

    def prepare_edit(self, parser, db_name, dbn):
        self.db_name = db_name
        self.dbn     = dbn
        if not self.config.has_database(self.db_name):
            parser.error('database not found')

    def start_edit(self):
        if self.config.add_database(self.db_name, self.dbn):
            print 'Database configured.'
        else:
            print 'No changes were made.'
