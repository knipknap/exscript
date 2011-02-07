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
from Exscriptd.Config               import Config
from Exscriptd.config.ConfigSection import ConfigSection

__dirname__ = os.path.dirname(__file__)
log_dir     = os.path.join('/var', 'log', 'exscriptd')
spool_dir   = os.path.join('/var', 'spool', 'exscriptd')
init_dir    = os.path.join('/etc', 'init.d')

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
        return (('install', 'install the daemon'),
                ('add',     'configure a new daemon'),
                ('edit',    'configure an existing daemon'))

    def _generate(self, infilename, outfilename):
        if not self.options.overwrite and os.path.isfile(outfilename):
            self.info('file exists, skipping.\n')
            return

        vars = {'@CFG_DIR@':    self.global_options.config_dir,
                '@LOG_DIR@':    self.options.log_dir,
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
        parser.add_option('--logdir',
                          dest    = 'log_dir',
                          metavar = 'STRING',
                          default = log_dir,
                          help    = 'the path where the logs are stored')

    def start_install(self):
        # Install the init script.
        init_template = os.path.join(__dirname__, 'exscriptd.in')
        init_file     = os.path.join('/etc', 'init.d', 'exscriptd')
        self.info('creating init-file at %s... ' % init_file)
        self._generate(init_template, init_file)
        mode = os.stat(init_file).st_mode
        os.chmod(init_file, mode|stat.S_IXUSR|stat.S_IXGRP|stat.S_IXOTH)

        # Create directories.
        self.info('creating log directory %s... ' % self.options.log_dir)
        self._mkdir(self.options.log_dir)
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
        parser.add_option('--logdir',
                          dest    = 'logdir',
                          metavar = 'STRING',
                          default = os.devnull,
                          help    = 'the path where the logs are stored')
        parser.add_option('--account-pool',
                          dest    = 'account_pool',
                          metavar = 'STRING',
                          help    = 'the account pool used for authenticating' \
                                  + 'HTTP clients')
        parser.add_option('--database',
                          dest    = 'database',
                          metavar = 'STRING',
                          help    = 'the name of the database')

    def prepare_add(self, parser, daemon_name):
        self.daemon_name = daemon_name
        self._read_config()
        if self.config.has_daemon(self.daemon_name):
            parser.error('daemon already exists')

    def start_add(self):
        self.config.add_daemon(self.daemon_name,
                               self.options.address,
                               self.options.port,
                               self.options.logdir,
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

    def start_edit(self):
        self.config.add_daemon(self.daemon_name,
                               self.options.address,
                               self.options.port,
                               self.options.logdir,
                               self.options.account_pool,
                               self.options.database)
        print 'Daemon configured.'
