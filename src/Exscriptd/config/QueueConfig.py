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

class QueueConfig(ConfigSection):
    def __init__(self, *args, **kwargs):
        ConfigSection.__init__(self, *args, **kwargs)
        self.queue_name = None
        self.config     = Config(self.global_options.config_dir, False)

    @staticmethod
    def get_description():
        return 'add, edit, or remove queues'

    @staticmethod
    def get_commands():
        return (('add',  'create a new queue'),
                ('edit', 'edit an existing queue'))

    def getopt_add(self, parser):
        parser.add_option('--account-pool',
                          dest    = 'account_pool',
                          metavar = 'STRING',
                          help    = 'the account pool that is used')
        parser.add_option('--max-threads',
                          dest    = 'max_threads',
                          metavar = 'INT',
                          default = 5,
                          help    = 'the name of the new queue')

    def prepare_add(self, parser, queue_name):
        self.queue_name = queue_name
        if self.config.has_queue(self.queue_name):
            parser.error('queue already exists')

    def start_add(self):
        self.config.add_queue(self.queue_name,
                              self.options.account_pool,
                              self.options.max_threads)
        print 'Queue added.'

    def getopt_edit(self, parser):
        self.getopt_add(parser)

    def prepare_edit(self, parser, queue_name):
        self.queue_name = queue_name
        if not self.config.has_queue(self.queue_name):
            parser.error('queue not found')

    def start_edit(self):
        if self.config.add_queue(self.queue_name,
                                 self.options.account_pool,
                                 self.options.max_threads):
            print 'Queue configured.'
        else:
            print 'No changes were made.'
