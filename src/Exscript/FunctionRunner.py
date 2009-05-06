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
import time, os, re, gc
from Job             import Job
from FuncJob         import FuncJob
from SpiffWorkQueue  import Sequence
from Host            import Host
from Account         import Account
from TerminalActions import *

True  = 1
False = 0

class FunctionRunner(Job):
    bracket_expression_re = re.compile(r'^\{([^\]]*)\}$')

    def __init__(self, func, *data, **kwargs):
        """
        Constructor.

        @type  kwargs: dict
        @param kwargs: The following options are supported:
            - define: Global variables.
            - host: Passed to add_host().
            - hosts: Passed to add_hosts().
            - hosts_file: Passed to add_hosts_from_file().
            - hosts_csv: Passed to add_hosts_from_csv().
            - verbose: The verbosity level of the interpreter.
            - domain: The default domain of the contacted hosts.
            - retry_login: The number of login retries, default 0.
            - logdir: The directory into which the logs are written.
            - overwrite_logs: Whether existing logfiles are overwritten.
            - no_prompt: Whether the compiled program should wait for a 
            prompt each time after the Exscript sent a command to the 
            remote host.
        """
        Job.__init__(self, **kwargs)
        self.hosts       = []
        self.options     = {}
        self.accounts    = {}
        self.func        = func
        self.data        = data
        self.set_options(**kwargs)


    def _dbg(self, level, msg):
        if level > self.verbose:
            return
        print msg


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


    def set_options(self, **kwargs):
        """
        Set the given options.
        """
        self.options.update(kwargs)
        self.no_prompt      = kwargs.get('no_prompt',      0)
        self.verbose        = kwargs.get('verbose',        0)
        self.retry_login    = kwargs.get('retry_login',    0)
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


    def add_host(self, uri):
        """
        Adds a single given host for executing the script later.

        @type  uri: string
        @param uri: A hostname, IP address, or a URI.
        """
        if isinstance(uri, Host):
            host = uri
        else:
            host = Host(uri)
        self.hosts.append(host)

        # Define host-specific variables.
        for key, val in host.vars.iteritems():
            if not isinstance(val[0], str):
                continue
            match = self.bracket_expression_re.match(val[0])
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


    def _get_sequence(self, exscript, host):
        if not host.get_domain():
            host.set_domain(self.options.get('domain', ''))

        # One logfile per host.
        logfile       = None
        error_logfile = None
        if self.options.get('logdir') is None:
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

        # Build the sequence.
        noecho       = self.options.get('no-echo',           False)
        av           = self.options.get('ssh-auto-verify',   None)
        nip          = self.options.get('no-initial-prompt', False)
        nop          = self.options.get('no-prompt',         False)
        authenticate = not self.options.get('no-authentication', False)
        echo         = exscript.get_max_threads() == 1 and not noecho
        wait         = not nip and not nop
        protocol_args = {'echo': echo, 'auto_verify': av}
        sequence.add(Connect(host, **protocol_args))
        if authenticate:
            account = self._get_account(exscript,
                                        host.get_username(),
                                        host.get_password())
            sequence.add(Authenticate(exscript.account_manager,
                                      account,
                                      wait = wait))

        sequence.add(FuncJob(exscript, self.func, *self.data))
        sequence.add(Close())
        sequence.signal_connect('aborted',
                                self._on_sequence_aborted,
                                exscript,
                                host)
        return sequence


    def _on_sequence_aborted(self,
                             sequence,
                             exception,
                             exscript,
                             host):
        if sequence.retry == 0:
            raise exception
        self._dbg(1, 'Retrying %s' % host.get_address())
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


    def run(self, exscript, **kwargs):
        n_connections   = exscript.get_max_threads()
        hosts           = self.hosts[:]
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
