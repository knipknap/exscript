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
import sys, time, os, re, gc, copy, threading
from Host            import Host
from Job             import Job
from Interpreter     import Parser
from SpiffWorkQueue  import Sequence
from Account         import Account
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
            - host: Passed to add_host().
            - hosts: Passed to add_hosts().
            - hosts_file: Passed to add_hosts_from_file().
            - hosts_csv: Passed to add_hosts_from_csv().
            - template_file: The template file to be executed.
            - template: The template to be executed.
            - verbose: The verbosity level of the interpreter.
            - parser_verbose: The verbosity level of the parser.
            - domain: The default domain of the contacted hosts.
            - retry_login: The number of login retries, default 0.
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
        self.host_list      = []
        self.vars           = {}
        self.options        = {}
        self.accounts       = {}
        self.parser         = None
        self.parser_lock    = threading.Lock()
        self.set_options(**kwargs)


    def set_options(self, **kwargs):
        """
        Set the given options of the template runner.
        """
        self.options.update(kwargs)
        self.parser_verbose = kwargs.get('parser_verbose', 0)
        self.no_prompt      = kwargs.get('no_prompt',      0)
        self.verbose        = kwargs.get('verbose',        0)
        self.retry_login    = kwargs.get('retry_login',    0)
        self.parser_lock.acquire()
        self.parser = self._get_parser()
        self.parser_lock.release()
        if self.options.get('define') is not None:
            self.define(**self.options.get('define'))
        if self.options.get('host') is not None:
            self.add_host(self.options.get('host'))
        if self.options.get('hosts') is not None:
            self.add_hosts(self.options.get('hosts'))
        if self.options.get('hosts_file') is not None:
            self.add_hosts_from_file(self.options.get('hosts_file'))
        if self.options.get('hosts_csv') is not None:
            self.add_hosts_from_csv(self.options.get('hosts_csv'))
        if self.options.has_key('template'):
            self.read_template(self.options.get('template'))
        if self.options.has_key('template_file'):
            self.read_template_from_file(self.options.get('template_file'))


    def _dbg(self, level, msg):
        if level > self.verbose:
            return
        print msg


    def _get_parser(self):
        return Parser(debug     = self.parser_verbose,
                      no_prompt = self.no_prompt)


    def _get_account(self, exscript, user, password, password2 = None):
        if user is None:
            return None
        account = self.accounts.get(user)
        if account is not None:
            return account
        account = exscript.account_manager.get_account_from_name(user)
        if account is not None:
            return account
        account = Account(user, password, password2)
        self.accounts[user] = account
        return account


    def add_host(self, uri):
        """
        Adds a single given host for executing the script later.

        @type  uri: string
        @param uri: A hostname, IP address, or a URI.
        """
        host = Host(uri)
        self.host_list.append(host)

        # Define host-specific variables.
        for key, val in host.vars.iteritems():
            match = TemplateRunner.bracket_expression_re.match(val[0])
            if match is not None:
                string = match.group(1) or 'a value for "%s"' % key
                val    = [raw_input('Please enter %s: ' % string)]
                host.define(key, val)

        return host


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
        last_uri = ''
        for line in file_handle:
            if line.strip() == '':
                continue

            line   = re.sub(r'[\r\n]*$', '', line)
            values = line.split('\t')
            uri    = values.pop(0).strip()

            # Add the hostname to our list.
            if uri != last_uri:
                #print "Reading hostname", hostname_url, "from csv."
                host     = self.add_host(uri)
                last_uri = uri

            # Define variables according to the definition.
            for i in range(0, len(varnames)):
                try:
                    value = values[i]
                except:
                    value = ''
                host.append(varnames[i], value)

        file_handle.close()


    def define(self, **kwargs):
        """
        Defines the given variables such that they may be accessed from 
        within the Exscript template.

        @type  kwargs: dict
        @param kwargs: Variables to make available to the Exscript.
        """
        self.vars.update(kwargs)


    def read_template(self, template):
        """
        Reads the given Exscript template, using the given options.
        MUST be called before run() is called, either directly or through 
        read_template_from_file().

        @type  template: string
        @param template: An Exscript template.
        """
        # Define variables.
        if len(self.host_list) == 0:
            host = Host('unknown')
            host.set('hostname', 'unknown')
        else:
            host = self.host_list[0]

        # Assign to the parser.
        self.parser_lock.acquire()
        self.parser.define(**self.vars)
        self.parser.define(**host.vars)
        self.parser.define(__filename__ = self.file)
        self.parser.define(hostname     = host.get_name())

        # Parse the Exscript.
        try:
            self.compiled = self.parser.parse(template)
            self.code     = template
        except Exception, e:
            self.parser_lock.release()
            if self.verbose > 0:
                raise
            print e
            sys.exit(1)
        self.parser_lock.release()


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


    def _get_sequence(self, exscript, host):
        """
        Compiles the current Exscript template, and returns a new workqueue 
        sequence for it that is initialized and has all the variables defined.
        """
        if self.compiled is None:
            msg = 'An Exscript was not yet read using read_template().'
            raise Exception(msg)

        # Pass variables to the Exscript interpreter.
        if not host.get_domain():
            host.set_domain(self.options.get('domain', ''))
        variables = dict()
        variables.update(self.vars)
        variables['hostname'] = host.get_address()
        variables.update(host.vars)
        self.parser_lock.acquire()
        self.parser.define(**variables)

        # Parse the Exscript template.
        #FIXME: In Python > 2.2 we can (hopefully) deep copy the object instead of
        # recompiling numerous times.
        if self.options.has_key('filename'):
            file = self.options.get('filename')
            try:
                compiled = self.parser.parse_file(file)
            except:
                self.parser_lock.release()
                raise
        else:
            code = self.options.get('code', self.code)
            try:
                compiled = self.parser.parse(code)
            except:
                self.parser_lock.release()
                raise
        self.parser_lock.release()

        #compiled = copy.deepcopy(self.compiled)
        compiled.init(**variables)
        compiled.define(__filename__ = self.file)
        compiled.define(__runner__   = self)
        compiled.define(__exscript__ = exscript)

        # One logfile per host.
        logfile       = None
        error_logfile = None
        if self.options['logdir'] is None:
            sequence = Sequence(name = host.get_address())
        else:
            logfile       = os.path.join(self.options['logdir'],
                                         host.get_address() + '.log')
            error_logfile = logfile + '.error'
            overwrite     = self.options.get('overwrite_logs', False)
            sequence      = LoggedSequence(name          = host.get_address(),
                                           logfile       = logfile,
                                           error_logfile = error_logfile,
                                           overwrite_log = overwrite)

        # Choose the protocol.
        if host.get_protocol() == 'dummy':
            protocol = __import__('termconnect.Dummy',
                                  globals(),
                                  locals(),
                                  'Dummy')
        elif host.get_protocol() == 'telnet':
            protocol = __import__('termconnect.Telnet',
                                  globals(),
                                  locals(),
                                  'Telnet')
        elif host.get_protocol() in ('ssh', 'ssh1', 'ssh2'):
            protocol = __import__('termconnect.SSH',
                                  globals(),
                                  locals(),
                                  'SSH')
        else:
            print 'ERROR: Unsupported protocol %s.' % repr(host.get_protocol())
            return None

        # Build the sequence.
        noecho       = self.options.get('no-echo',           False)
        av           = self.options.get('ssh-auto-verify',   None)
        nip          = self.options.get('no-initial-prompt', False)
        nop          = self.options.get('no-prompt',         False)
        authenticate = not self.options.get('no-authentication', False)
        echo         = exscript.get_max_threads() == 1 and not noecho
        wait         = not nip and not nop
        if host.get_protocol() == 'ssh1':
            ssh_version = 1
        elif host.get_protocol() == 'ssh2':
            ssh_version = 2
        else:
            ssh_version = None # auto-select
        protocol_args = {'echo':        echo,
                         'auto_verify': av,
                         'ssh_version': ssh_version}
        if host.get_tcp_port() is not None:
            protocol_args['port'] = host.get_tcp_port()

        sequence.add(Connect(protocol, host.get_address(), **protocol_args))
        if authenticate:
            account = self._get_account(exscript,
                                        host.get_username(),
                                        host.get_password())
            sequence.add(Authenticate(exscript.account_manager,
                                      account,
                                      wait = wait))
        sequence.add(CommandScript(compiled))
        sequence.add(Close())
        sequence.signal_connect('aborted',
                                self._on_sequence_aborted,
                                exscript,
                                host,
                                compiled)
        sequence.signal_connect('succeeded',
                                self._on_sequence_succeeded,
                                host,
                                compiled)
        return sequence


    def _copy_variables_from_thread(self, host, compiled):
        #vars = compiled.get_vars()
        #if vars.has_key('hostname'):
        #    del vars['hostname']
        #self.define_host(hostname, **vars)
        pass


    def _on_sequence_aborted(self,
                             sequence,
                             exception,
                             exscript,
                             host,
                             compiled):
        if sequence.retry == 0:
            self._copy_variables_from_thread(host, compiled)
            raise exception
        self._dbg(1, 'Retrying %s' % host.get_address())
        self._dbg(5, 'Retrying with code: %s' % repr(self.code))
        new_sequence       = self._get_sequence(exscript, host)
        new_sequence.retry = sequence.retry - 1
        retry              = self.retry_login - new_sequence.retry
        new_sequence.name  = new_sequence.name + ' (retry %d)' % retry
        logfile            = '%s_retry%d.log' % (host.get_address(), retry)
        logfile            = os.path.join(self.options['logdir'], logfile)
        error_logfile      = logfile + '.error'
        new_sequence.set_logfile(logfile)
        new_sequence.set_error_logfile(error_logfile)
        exscript._priority_enqueue_action(new_sequence)


    def _on_sequence_succeeded(self, sequence, host, compiled):
        self._copy_variables_from_thread(host, compiled)


    def run(self, exscript):
        n_connections   = exscript.get_max_threads()
        hosts           = self.host_list[:]
        exscript.total += len(hosts)

        for host in hosts:
            # To save memory, limit the number of parsed (=in-memory) items.
            # A side effect is that Exscript will no longer know the total
            # number of jobs - to work around this, we first add the total
            # ourselfs (see above), and then subtract one from the total 
            # each time a new host is appended (see below).
            while exscript.workqueue.get_length() > n_connections * 2:
                time.sleep(1)
                gc.collect()

            self._dbg(1, 'Building sequence for %s.' % host.get_name())
            sequence       = self._get_sequence(exscript, host)
            sequence.retry = self.retry_login
            if sequence is not None:
                exscript._enqueue_action(sequence)
                exscript.total -= 1
