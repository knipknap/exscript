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
import util
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
            - host: Passed to add_host().
            - hosts: Passed to add_hosts().
            - verbose: The verbosity level of the interpreter.
            - domain: The default domain of the contacted hosts.
            - retry_login: The number of login retries, default 0.
            - logdir: The directory into which the logs are written.
            - overwrite_logs: Whether existing logfiles are overwritten.
            - delete_logs: Whether successful logfiles are deleted.
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
        self.verbose     = kwargs.get('verbose',     0)
        self.retry_login = kwargs.get('retry_login', 0)
        if self.options.get('host') is not None:
            self.add_host(self.options.get('host'))
        if self.options.get('hosts') is not None:
            self.add_hosts(self.options.get('hosts'))


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
            try:
                val = val[0]
            except:
                val = None
            if not isinstance(val, str):
                continue
            match = self.bracket_expression_re.match(val)
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
            delete_logs   = self.options.get('delete_logs',    False)
            sequence      = LoggedSequence(name          = host.get_address(),
                                           logfile       = logfile,
                                           error_logfile = error_logfile,
                                           delete_log    = delete_logs,
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
        sequence.add(Connect(exscript, host, **protocol_args))
        if authenticate:
            account = self._get_account(exscript,
                                        host.get_username(),
                                        host.get_password())
            sequence.add(Authenticate(account, wait = wait))

        sequence.add(FuncJob(exscript, self.func, *self.data))
        sequence.add(Close(True))
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
            raise # exception
        self._dbg(1, 'Retrying %s' % host.get_address())
        new_sequence       = self._get_sequence(exscript, host)
        new_sequence.retry = sequence.retry - 1
        retry              = self.retry_login - new_sequence.retry
        new_sequence.name  = new_sequence.name + ' (retry %d)' % retry
        if self.options.get('logdir'):
            logfile       = '%s_retry%d.log' % (host.get_address(), retry)
            logfile       = os.path.join(self.options['logdir'], logfile)
            error_logfile = logfile + '.error'
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
