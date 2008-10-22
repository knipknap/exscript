# Copyright (C) 2007 Samuel Abels, http://debain.org
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
import sys, time, os, re, gc, copy
from Job             import Job
from Interpreter     import Parser
from FooLib          import UrlParser
from SpiffWorkQueue  import Sequence
from TerminalActions import *

True  = 1
False = 0

class TemplateRunner(Job):
    """
    Opens and parses an exscript template and executes it on one or 
    more hosts.
    """
    bracket_expression_re = re.compile(r'^\{([^\]]*)\}$')

    def __init__(self, **kwargs):
        """
        Constructor.

        @type  kwargs: dict
        @param kwargs: The following options are supported:
            - define: Global variables.
            - template_file: The template file to be executed.
            - template: The template to be executed.
            - verbose: The verbosity level of the interpreter.
            - parser_verbose: The verbosity level of the parser.
            - domain: The default domain of the contacted hosts.
            - logdir: The directory into which the logs are written.
            - overwrite_logs: Whether existing logfiles are overwritten.
            - no_prompt: Whether the compiled program should wait for a 
            prompt each time after the Exscript sent a command to the 
            remote host.
        """
        Job.__init__(self, **kwargs)
        self.compiled       = None
        self.code           = None
        self.file           = None
        self.hostnames      = []
        self.host_defines   = {}
        self.global_defines = {}
        self.options        = {}
        self.parser         = Parser(debug     = kwargs.get('parser_verbose', 0),
                                     no_prompt = kwargs.get('no_prompt',      0))
        self.set_options(**kwargs)


    def set_options(self, **kwargs):
        """
        Set the given options of the template runner.
        """
        self.options.update(kwargs)
        if self.options.get('define') is not None:
            self.define(**self.options.get('define'))
        if self.options.get('host') is not None:
            self.add_host(self.options.get('host'))
        if self.options.get('hosts') is not None:
            self.add_hosts(self.options.get('hosts'))
        if self.options.has_key('template'):
            self.read_template(self.options.get('template'))
        if self.options.has_key('template_file'):
            self.read_template_from_file(self.options.get('template_file'))


    def add_host(self, host):
        """
        Adds a single given host for executing the script later.

        @type  host: string
        @param host: A hostname or an IP address.
        """
        self.hostnames.append(host)
        url = UrlParser.parse_url(host)
        for key, val in url.vars.iteritems():
            match = TemplateRunner.bracket_expression_re.match(val[0])
            if match is None:
                continue
            string = match.group(1) or 'a value for "%s"' % key
            val    = raw_input('Please enter %s: ' % string)
            url.vars[key] = [val]
        self.host_defines[host] = url.vars


    def add_hosts(self, hosts):
        """
        Adds the given list of hosts for executing the script later.

        @type  hosts: list[string]
        @param hosts: A list of hostnames or IP addresses.
        """
        for host in hosts:
            self.add_host(host)


    def add_hosts_from_file(self, filename):
        """
        Reads a list of hostnames from the file with the given name.

        @type  filename: string
        @param filename: A full filename.
        """
        # Open the file.
        if not os.path.exists(filename):
            raise IOError('No such file: %s' % filename)
        file_handle = open(filename, 'r')

        # Read the hostnames.
        for line in file_handle:
            hostname = line.strip()
            if hostname == '':
                continue
            self.add_host(hostname)

        file_handle.close()


    def add_hosts_from_csv(self, filename):
        """
        Reads a list of hostnames and variables from the .csv file with the 
        given name.

        @type  filename: string
        @param filename: A full filename.
        """
        # Open the file.
        if not os.path.exists(filename):
            raise IOError('No such file: %s' % filename)
        file_handle = open(filename, 'r')

        # Read the header.
        header = file_handle.readline().rstrip()
        if re.search(r'^hostname\b', header) is None:
            msg  = 'Syntax error in CSV file header:'
            msg += ' File does not start with "hostname".'
            raise Exception(msg)
        if re.search(r'^hostname(?:\t[^\t]+)*$', header) is None:
            msg  = 'Syntax error in CSV file header:'
            msg += ' Make sure to separate columns by tabs.'
            raise Exception(msg)
        varnames = header.split('\t')
        varnames.pop(0)

        # Walk through all lines and create a map that maps hostname to definitions.
        last_hostname = ''
        for line in file_handle:
            line         = re.sub(r'[\r\n]*$', '', line)
            values       = line.split('\t')
            hostname_url = values.pop(0).strip()
            hostname     = UrlParser.parse_url(hostname_url).hostname

            # Add the hostname to our list.
            if hostname != last_hostname:
                #print "Reading hostname", hostname, "from csv."
                self.add_host(hostname_url)
                last_hostname = hostname

            # Define variables according to the definition.
            for i in range(0, len(varnames)):
                varname = varnames[i]
                try:
                    value = values[i]
                except:
                    value = ''
                if self.host_defines[hostname].has_key(varname):
                    self.host_defines[hostname][varname].append(value)
                else:
                    self.host_defines[hostname][varname] = [value]

        file_handle.close()


    def define(self, **kwargs):
        """
        Defines the given variables such that they may be accessed from 
        within the Exscript template.

        @type  kwargs: dict
        @param kwargs: Variables to make available to the Exscript.
        """
        self.global_defines.update(kwargs)


    def define_host(self, hostname, **kwargs):
        """
        Defines the given variables such that they may be accessed from 
        within the Exscript template only while logged into the specified 
        hostname.

        @type  hostname: string
        @param hostname: A hostname or an IP address.
        @type  kwargs: dict
        @param kwargs: Variables to make available to the Exscript.
        """
        if not self.host_defines.has_key(hostname):
            self.host_defines[hostname] = {}
        self.host_defines[hostname].update(kwargs)


    def read_template(self, template):
        """
        Reads the given Exscript template, using the given options.
        MUST be called before run() is called, either directly or through 
        read_template_from_file().

        @type  template: string
        @param template: An Exscript template.
        """
        # Parse the exscript.
        self.parser.define(**self.global_defines)
        self.parser.define(**self.host_defines[self.hostnames[0]])
        self.parser.define(__filename__ = self.file)
        self.parser.define(hostname     = self.hostnames[0])
        try:
            self.compiled = self.parser.parse(template)
            self.code     = template
        except Exception, e:
            if self.verbose > 0:
                raise
            print e
            sys.exit(1)


    def read_template_from_file(self, filename):
        """
        Loads the Exscript file with the given name, and calls 
        read_template() to process the code using the given options.

        @type  filename: string
        @param filename: A full filename.
        """
        file_handle = open(filename, 'r')
        self.file   = filename
        template    = file_handle.read()
        file_handle.close()
        self.read_template(template)


    def _get_sequence(self, exscript, hostname):
        """
        Compiles the current Exscript template, and returns a new workqueue 
        sequence for it that is initialized and has all the variables defined.
        """
        if self.compiled is None:
            msg = 'An Exscript was not yet read using read_template().'
            raise Exception(msg)

        # Prepare variables that are passed to the Exscript interpreter.
        user             = self.options.get('user')
        password         = self.options.get('password')
        default_protocol = self.options.get('protocol', 'telnet')
        url              = UrlParser.parse_url(hostname, default_protocol)
        this_proto       = url.protocol
        this_user        = url.username
        this_password    = url.password
        this_host        = url.hostname
        domain           = self.options.get('domain', '')
        if not '.' in this_host and len(domain) > 0:
            this_host += '.' + domain
        variables = dict()
        variables.update(self.global_defines)
        variables.update(self.host_defines[hostname])
        variables['hostname'] = this_host
        variables.update(url.vars)
        if this_user is None:
            this_user = user
        if this_password is None:
            this_password = password

        #FIXME: In Python > 2.2 we can (hopefully) deep copy the object instead of
        # recompiling numerous times.
        self.parser.define(**variables)
        if self.options.has_key('filename'):
            file     = self.options.get('filename')
            compiled = self.parser.parse_file(file)
        else:
            code     = self.options.get('code', self.code)
            compiled = self.parser.parse(code)
        #compiled = copy.deepcopy(self.compiled)
        compiled.init(**variables)
        compiled.define(__filename__ = self.file)
        compiled.define(__runner__   = self)
        compiled.define(__exscript__ = exscript)

        # One logfile per host.
        logfile       = None
        error_logfile = None
        if self.options['logdir'] is None:
            sequence = Sequence(name = this_host)
        else:
            logfile       = os.path.join(self.options['logdir'],
                                         this_host + '.log')
            error_logfile = logfile + '.error'
            overwrite     = self.options.get('overwrite_logs', False)
            sequence      = LoggedSequence(name          = this_host,
                                           logfile       = logfile,
                                           error_logfile = error_logfile,
                                           overwrite_log = overwrite)

        # Choose the protocol.
        if this_proto == 'telnet':
            protocol = __import__('termconnect.Telnet',
                                  globals(),
                                  locals(),
                                  'Telnet')
        elif this_proto in ('ssh', 'ssh1', 'ssh2'):
            protocol = __import__('termconnect.SSH',
                                  globals(),
                                  locals(),
                                  'SSH')
        else:
            print 'Unsupported protocol %s' % this_proto
            return None

        # Build the sequence.
        noecho       = self.options.get('no-echo',           False)
        key          = self.options.get('ssh-key',           None)
        av           = self.options.get('ssh-auto-verify',   None)
        nip          = self.options.get('no-initial-prompt', False)
        nop          = self.options.get('no-prompt',         False)
        authenticate = not self.options.get('no-authentication', False)
        echo         = exscript.get_max_threads() == 1 and not noecho
        wait         = not nip and not nop
        if this_proto == 'ssh1':
            ssh_version = 1
        elif this_proto == 'ssh2':
            ssh_version = 2
        else:
            ssh_version = None # auto-select
        protocol_args = {'echo':        echo,
                         'auto_verify': av,
                         'ssh_version': ssh_version}
        if url.port is not None:
            protocol_args['port'] = url.port
        sequence.add(Connect(protocol, this_host, **protocol_args))
        if key is None and authenticate:
            sequence.add(Authenticate(this_user,
                                      password = this_password,
                                      wait     = wait))
        elif authenticate:
            sequence.add(Authenticate(this_user,
                                      key_file = key,
                                      wait     = wait))
        sequence.add(CommandScript(compiled))
        sequence.add(Close())
        return sequence


    def run(self, exscript):
        n_connections = exscript.get_max_threads()

        for hostname in self.hostnames[:]:
            # To save memory, limit the number of parsed (=in-memory) items.
            while exscript.workqueue.get_length() > n_connections * 2:
                time.sleep(1)
                gc.collect()

            self._dbg(1, 'Building sequence for %s.' % hostname)
            sequence = self._get_sequence(exscript, hostname)
            exscript.workqueue.enqueue(sequence)
