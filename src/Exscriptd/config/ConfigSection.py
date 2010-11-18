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

class ConfigSection(object):
    def __init__(self, global_options, script_dir):
        self.global_options = global_options
        self.options        = None
        self.script_dir     = script_dir

    @staticmethod
    def get_description():
        raise NotImplementedError()

    @staticmethod
    def get_commands():
        raise NotImplementedError()

    def _mkdir(self, dirname):
        if os.path.isdir(dirname):
            self.info('directory exists, skipping.\n')
        else:
            os.makedirs(dirname)
            self.info('done.\n')

    def info(self, *args):
        sys.stdout.write(' '.join(str(a) for a in args))

    def error(self, *args):
        sys.stderr.write(' '.join(str(a) for a in args))
