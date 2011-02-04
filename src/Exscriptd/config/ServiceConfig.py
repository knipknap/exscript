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
import sys
from Exscriptd.util                 import find_module_recursive
from Exscriptd.Config               import Config
from Exscriptd.config.ConfigSection import ConfigSection

class ServiceConfig(ConfigSection):
    def __init__(self, *args, **kwargs):
        ConfigSection.__init__(self, *args, **kwargs)
        self.service_name = None
        self.module_name  = None
        self.varname      = None
        self.value        = None
        self.config       = Config(self.global_options.config_dir, False)

    @staticmethod
    def get_description():
        return 'add or configure services'

    @staticmethod
    def get_commands():
        return (('add',   'configure a new service'),
                ('edit',  'configure an existing service'),
                ('set',   'define a service variable'),
                ('unset', 'remove a service variable'))

    def _assert_module_exists(self, parser, module_name):
        try:
            file, module_path, desc = find_module_recursive(module_name)
        except ImportError:
            args = repr(module_name), sys.path
            msg  = 'service %s not found. sys.path is %s' % args
            parser.error(msg)

    def getopt_add(self, parser):
        parser.add_option('--daemon',
                          dest    = 'daemon',
                          metavar = 'STRING',
                          help    = 'the daemon that is used')
        parser.add_option('--queue',
                          dest    = 'queue',
                          metavar = 'STRING',
                          help    = 'the queue that is used')

    def prepare_add(self, parser, service_name, module_name):
        self.service_name = service_name
        self.module_name  = module_name
        self._assert_module_exists(parser, module_name)
        if self.config.has_service(self.service_name):
            parser.error('service already exists')

    def start_add(self):
        self.config.add_service(self.service_name,
                                self.module_name,
                                self.options.daemon,
                                self.options.queue)
        print 'Service added.'

    def getopt_edit(self, parser):
        self.getopt_add(parser)

    def prepare_edit(self, parser, service_name):
        self.service_name = service_name
        if not self.config.has_service(self.service_name):
            parser.error('service not found')

    def start_edit(self):
        if self.config.add_service(self.service_name,
                                   None,
                                   self.options.daemon,
                                   self.options.queue):
            print 'Service configured.'
        else:
            print 'No changes were made.'

    def prepare_set(self, parser, service_name, varname, value):
        self.service_name = service_name
        self.varname      = varname
        self.value        = value

    def start_set(self):
        self.config.set_service_variable(self.service_name,
                                         self.varname,
                                         self.value)
        print 'Variable set.'

    def prepare_unset(self, parser, service_name, varname):
        self.service_name = service_name
        self.varname      = varname

    def start_unset(self):
        self.config.unset_service_variable(self.service_name, self.varname)
        print 'Variable removed.'
