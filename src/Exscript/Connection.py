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
import threading

True  = 1
False = 0

protocol_map = {'dummy':  'Dummy',
                'telnet': 'Telnet',
                'ssh':    'SSH',
                'ssh1':   'SSH',
                'ssh2':   'SSH'}

class Connection(object):
    def __init__(self, exscript, host, **kwargs):
        # Since we override setattr below, we can't access our properties
        # directly.
        self.__dict__['exscript']     = exscript
        self.__dict__['host']         = host
        self.__dict__['last_account'] = None

        # Find the Python module of the requested protocol.
        module_name = protocol_map.get(host.get_protocol())
        if module_name:
            protocol = __import__('termconnect.' + module_name,
                                  globals(),
                                  locals(),
                                  module_name)
        else:
            name = repr(host.get_protocol())
            raise Exception('ERROR: Unsupported protocol %s.' % name)

        # Define protocol specific options.
        if host.get_protocol() == 'ssh1':
            kwargs['ssh_version'] = 1
        elif host.get_protocol() == 'ssh2':
            kwargs['ssh_version'] = 2
        else:
            kwargs['ssh_version'] = None
        if host.get_tcp_port() is not None:
            kwargs['port'] = host.get_tcp_port()

        # Create an instance of the protocol adapter.
        self.__dict__['transport'] = protocol.Transport(**kwargs)

    def __setattr__(self, name, value):
        if name in self.__dict__.keys():
            self.__dict__[name] = value
        else:
            setattr(self.transport, name, value)

    def __getattr__(self, name):
        if name in self.__dict__.keys():
            return self.__dict__[name]
        return getattr(self.transport, name)

    def _on_otp_requested(self, key, seq, account):
        account.signal_emit('otp_requested', account, key, seq)

    def _acquire_account(self, account = None, lock = True):
        if account and lock:
            account.acquire()
        elif account:
            pass
        elif self.last_account and lock:
            account = self.last_account
            account.acquire()
        elif self.last_account:
            account = self.last_account
        elif lock:
            account = self.get_account_manager().acquire_account()
        else:
            raise Exception('Non-locking shared accounts unsupported.')
        self.last_account = account
        self.transport.set_on_otp_requested_cb(self._on_otp_requested,
                                               account)
        return account

    def _release_account(self, account = None):
        self.transport.set_on_otp_requested_cb(None)
        if account == self.last_account:
            account = None
        if account:
            account.release()
        elif self.last_account:
            self.last_account.release()
            self.last_account = None
        else:
            raise Exception('Attempt to relase a released account.')

    def get_exscript(self):
        return self.exscript

    def get_account_manager(self):
        return self.exscript.account_manager

    def get_host(self):
        return self.host

    def open(self):
        if not self.transport.connect(self.host.get_address(),
                                      self.host.get_tcp_port()):
            raise Exception('Connection failed.')

    def close(self, force = False):
        self.transport.close(force)

    def authenticate(self, account = None, wait = False, lock = True):
        account  = self._acquire_account(account, lock)
        key_file = account.options.get('ssh_key_file')

        try:
            self.transport.authenticate(account.get_name(),
                                        account.get_password(),
                                        wait     = wait,
                                        key_file = key_file)
        except:
            if lock:
                self._release_account(account)
            raise
        if lock:
            self._release_account(account)
        return account

    def authorize(self, account = None, wait = False, lock = True):
        account  = self._acquire_account(account, lock)
        key_file = account.options.get('ssh_key_file')

        try:
            self.transport.authorize(account.get_authorization_password(),
                                     wait = wait)
        except:
            if lock:
                self._release_account(account)
            raise
        if lock:
            self._release_account(account)
        return account

    def auto_authorize(self, account = None, wait = True, password = None):
        os       = self.guess_os()
        account  = self._acquire_account(account)
        commands = {'ios': 'enable\r', 'junos': None}
        command  = commands.get(os)

        if password is None:
            password = account.get_authorization_password()

        try:
            if command:
                self.send(command)
                self.transport.authorize(password, wait = wait)
        except:
            self._release_account(account)
            raise
        self._release_account(account)
        return account
