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
import sys
from lxml             import etree
from ConfigSection    import ConfigSection
from Exscriptd.util   import find_module_recursive
from Exscriptd.Config import Config

class ServiceConfig(ConfigSection):
    service_name = None
    module_name  = None

    def prepare_add(self, parser, service_name, module_name):
        self.service_name = service_name
        self.module_name  = module_name
        try:
            file, module_path, desc = find_module_recursive(module_name)
        except ImportError:
            args = repr(module_name), sys.path
            msg  = 'service %s not found. sys.path is %s' % args
            parser.error(msg)

    def start_add(self):
        config = Config(self.options.config_dir)
        if config.add_service(self.service_name, self.module_name):
            print 'Service added.'
        else:
            print 'Service already exists, no changes were made.'
