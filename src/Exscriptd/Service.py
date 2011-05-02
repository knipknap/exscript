# Copyright (C) 2007-2010 Samuel Abels.
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
from collections            import defaultdict
from threading              import Lock
from Exscriptd.Task         import Task
from Exscriptd.ConfigReader import ConfigReader

class Service(object):
    def __init__(self,
                 parent,
                 name,
                 cfg_dir,
                 main_cfg,
                 queue_name = None):
        self.parent     = parent
        self.name       = name
        self.cfg_dir    = cfg_dir
        self.main_cfg   = main_cfg
        self.queue_name = queue_name
        self.parent.service_added(self)

    def get_queue_name(self):
        return self.queue_name

    def get_config_file(self, name):
        return os.path.join(self.cfg_dir, name)

    def load_config_file(self, name, parser = ConfigReader):
        path = self.config_file(name)
        return parser(path, parent = self.main_cfg)

    def check(self, order):
        return True

    def enter(self, order):
        return True
