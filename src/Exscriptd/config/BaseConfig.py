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
import stat
import re
from Exscriptd.Config import Config, default_log_dir
from Exscriptd.config.ConfigSection import ConfigSection

__dirname__ = os.path.dirname(__file__)
spool_dir   = os.path.join('/var', 'spool', 'exscriptd')
pidfile     = os.path.join('/var', 'run', 'exscriptd.pid')
init_dir    = os.path.join('/etc', 'init.d')

class BaseConfig(ConfigSection):
    def __init__(self, *args, **kwargs):
        ConfigSection.__init__(self, *args, **kwargs)
        self.config = None

    def _read_config(self):
        self.config = Config(self.global_options.config_dir, False)

    @staticmethod
    def get_description():
        return 'global base configuration'

    @staticmethod
    def get_commands():
        return (('install', 'install exscriptd base config'),
                ('edit',    'change the base config'))

    def _generate(self, infilename, outfilename):
        if not self.options.overwrite and os.path.isfile(outfilename):
            self.info('file exists, skipping.\n')
            return

        vars = {'@CFG_DIR@':    self.global_options.config_dir,
                '@LOG_DIR@':    self.options.log_dir,
                '@SPOOL_DIR@':  spool_dir,
                '@SCRIPT_DIR@': self.script_dir,
                '@PYTHONPATH@': os.environ.get('PYTHONPATH'),
                '@PIDFILE@':    self.options.pidfile,
                '@INIT_DIR@':   init_dir}
        sub_re = re.compile('(' + '|'.join(vars.keys()) + ')+')

        with open(infilename) as infile:
            content = infile.read()
        subst   = lambda s: vars[s.group(0)]
        content = sub_re.sub(subst, content)
        with open(outfilename, 'w') as outfile:
            outfile.write(content)
        self.info('done.\n')

    def getopt_install(self, parser):
        self.getopt_edit(parser)
        parser.add_option('--overwrite',
                          dest    = 'overwrite',
                          action  = 'store_true',
                          default = False,
                          help    = 'overwrite existing files')
        parser.add_option('--pidfile',
                          dest    = 'pidfile',
                          metavar = 'STRING',
                          default = pidfile,
                          help    = 'the location of the pidfile')

    def _make_executable(self, filename):
        self.info('making %s executable...\n' % filename)
        mode = os.stat(filename).st_mode
        os.chmod(filename, mode|stat.S_IXUSR|stat.S_IXGRP|stat.S_IXOTH)

    def _create_directories(self):
        log_dir = self.options.log_dir
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

    def start_install(self):
        # Install the init script.
        init_template = os.path.join(__dirname__, 'exscriptd.in')
        init_file     = os.path.join('/etc', 'init.d', 'exscriptd')
        self.info('creating init-file at %s... ' % init_file)
        self._generate(init_template, init_file)
        self._make_executable(init_file)

        # Create directories.
        self._create_directories()

        # Install the default config file.
        cfg_tmpl = os.path.join(__dirname__, 'main.xml.in')
        cfg_file = os.path.join(self.global_options.config_dir, 'main.xml')
        self.info('creating config file %s... ' % cfg_file)
        self._generate(cfg_tmpl, cfg_file)

    def getopt_edit(self, parser):
        parser.add_option('--log-dir',
                          dest    = 'log_dir',
                          default = default_log_dir,
                          metavar = 'FILE',
                          help    = 'where to place log files')

    def prepare_edit(self, parser):
        self._read_config()
        cfg_file = os.path.join(self.global_options.config_dir, 'main.xml')
        if not os.path.exists(cfg_file):
            parser.error('no existing base installation found')

    def start_edit(self):
        self._create_directories()
        self.config.set_logdir(self.options.log_dir)
        print 'Base configuration saved.'
