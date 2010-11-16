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
import re
from ConfigSection import ConfigSection

__dirname__   = os.path.dirname(__file__)
init_template = os.path.join(__dirname__, 'exscriptd.in')

class DaemonConfig(ConfigSection):
    def _generate(self, infilename, outfilename):
        vars = {'@CFG_DIR@':    self.options.config_dir,
                '@SCRIPT_DIR@': self.script_dir,
                '@INIT_DIR@':   os.path.join('/etc', 'init.d')}
        sub_re = re.compile('(' + '|'.join(vars.keys()) + ')+')

        content = open(infilename).read()
        subst   = lambda s: vars[s.group(0)]
        content = sub_re.sub(subst, content)
        outfile = open(outfilename, 'w')
        outfile.write(content)
        outfile.close()

    def install(self):
        self._generate(init_template, '/home/sab/exscriptd.test')
        #self._generate(init_template, '/etc/init.d/exscriptd')
