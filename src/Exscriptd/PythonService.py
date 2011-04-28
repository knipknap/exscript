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
import __builtin__
import sys
import os
from Exscriptd.Service import Service
from Exscriptd.util    import find_module_recursive

class PythonService(Service):
    def __init__(self,
                 daemon,
                 name,
                 module,
                 cfg_dir,
                 logdir,
                 main_cfg,
                 queue = None):
        Service.__init__(self,
                         daemon,
                         name,
                         cfg_dir,
                         logdir,
                         main_cfg,
                         queue = queue)
        try:
            fp, filename, description = find_module_recursive(module)
        except ImportError:
            raise Exception('invalid module name: %s' % module)
        filename = os.path.join(filename, 'service.py')
        with open(filename) as file:
            content = file.read()
        code                 = compile(content, filename, 'exec')
        vars                 = {}
        vars['__builtin__']  = __builtin__
        vars['__file__']     = filename
        vars['__service__']  = self
        vars['__main_cfg__'] = self.main_cfg

        # Load the module using evil path manipulation, but oh well...
        # can't think of a sane way to do this.
        sys.path.insert(0, os.path.dirname(filename))
        result = eval(code, vars)
        sys.path.pop(0)

        self.check_func = vars.get('check')
        self.enter_func = vars.get('enter')

        if not self.enter_func:
            msg = filename + ': required function enter() not found.'
            raise Exception(msg)

    def check(self, order):
        if self.check_func:
            return self.check_func(order)
        return True

    def enter(self, order):
        return self.enter_func(order)
