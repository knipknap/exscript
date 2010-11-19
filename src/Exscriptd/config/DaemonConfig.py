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

__dirname__ = os.path.dirname(__file__)
log_dir     = os.path.join('/var', 'log', 'exscriptd')
spool_dir   = os.path.join('/var', 'spool', 'exscriptd')
init_dir    = os.path.join('/etc', 'init.d')

class DaemonConfig(ConfigSection):
    @staticmethod
    def get_description():
        return 'daemon-specific configuration'

    @staticmethod
    def get_commands():
        return (('install', 'install the daemon'),)

    def _generate(self, infilename, outfilename):
        if not self.options.overwrite and os.path.isfile(outfilename):
            self.info('file exists, skipping.\n')
            return

        vars = {'@CFG_DIR@':    self.global_options.config_dir,
                '@LOG_DIR@':    log_dir,
                '@SPOOL_DIR@':  spool_dir,
                '@SCRIPT_DIR@': self.script_dir,
                '@INIT_DIR@':   init_dir}
        sub_re = re.compile('(' + '|'.join(vars.keys()) + ')+')

        content = open(infilename).read()
        subst   = lambda s: vars[s.group(0)]
        content = sub_re.sub(subst, content)
        outfile = open(outfilename, 'w')
        outfile.write(content)
        outfile.close()
        self.info('done.\n')

    def getopt_install(self, parser):
        parser.add_option('--overwrite',
                          dest    = 'overwrite',
                          action  = 'store_true',
                          default = False,
                          help    = 'overwrite existing files')

    def start_install(self):
        # Install the init script.
        init_template = os.path.join(__dirname__, 'exscriptd.in')
        init_file     = os.path.join('/etc', 'init.d', 'exscriptd')
        self.info('creating init-file at %s... ' % init_file)
        self._generate(init_template, init_file)

        # Create directories.
        self.info('creating log directory %s... ' % log_dir)
        self._mkdir(log_dir)
        self.info('creating spool directory %s... ' % spool_dir)
        self._mkdir(spool_dir)
        cfg_dir = self.global_options.config_dir
        self.info('creating config directory %s... ' % cfg_dir)
        self._mkdir(cfg_dir)
        service_dir = os.path.join(cfg_dir, 'services')
        self.info('creating service directory %s... ' % service_dir)
        self._mkdir(service_dir)

        # Install the default config file.
        cfg_template = os.path.join(__dirname__, 'main.xml.in')
        cfg_file     = os.path.join(cfg_dir, 'main.xml')
        self.info('creating config file %s... ' % cfg_file)
        self._generate(cfg_template, cfg_file)
