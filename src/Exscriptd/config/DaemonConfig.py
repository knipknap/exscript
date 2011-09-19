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
from Exscriptd.Config import Config
from Exscriptd.config.ConfigSection import ConfigSection

class DaemonConfig(ConfigSection):
    def __init__(self, *args, **kwargs):
        ConfigSection.__init__(self, *args, **kwargs)
        self.daemon_name = None
        self.config      = None

    def _read_config(self):
        self.config = Config(self.global_options.config_dir, False)

    @staticmethod
    def get_description():
        return 'daemon-specific configuration'

    @staticmethod
    def get_commands():
        return (('add',  'configure a new daemon'),
                ('edit', 'configure an existing daemon'))

    def getopt_add(self, parser):
        parser.add_option('--address',
                          dest    = 'address',
                          metavar = 'STRING',
                          help    = 'the address to listen on, all by default')
        parser.add_option('--port',
                          dest    = 'port',
                          metavar = 'INT',
                          default = 8132,
                          help    = 'the TCP port number')
        parser.add_option('--database',
                          dest    = 'database',
                          metavar = 'STRING',
                          help    = 'name of the order database')
        parser.add_option('--account-pool',
                          dest    = 'account_pool',
                          metavar = 'STRING',
                          help    = 'the account pool used for authenticating' \
                                  + 'HTTP clients')

    def prepare_add(self, parser, daemon_name):
        self.daemon_name = daemon_name
        self._read_config()
        if self.config.has_daemon(self.daemon_name):
            parser.error('daemon already exists')

    def start_add(self):
        self.config.add_daemon(self.daemon_name,
                               self.options.address,
                               self.options.port,
                               self.options.account_pool,
                               self.options.database)
        print 'Daemon added.'

    def getopt_edit(self, parser):
        self.getopt_add(parser)

    def prepare_edit(self, parser, daemon_name):
        self.daemon_name = daemon_name
        self._read_config()
        if not self.config.has_daemon(self.daemon_name):
            parser.error('daemon not found')
        if not self.config.has_database(self.options.database):
            parser.error('database not found')

    def start_edit(self):
        self.config.add_daemon(self.daemon_name,
                               self.options.address,
                               self.options.port,
                               self.options.account_pool,
                               self.options.database)
        print 'Daemon configured.'
