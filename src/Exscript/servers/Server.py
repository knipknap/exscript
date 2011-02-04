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
"""
Base class for all servers.
"""
import socket
from multiprocessing import Process, Pipe

class Server(Process):
    """
    Base class of all servers. Servers are intended to be used for
    tests and attempt to emulate a device using the behavior of the
    associated L{Exscript.emulators.VirtualDevice}. Sample usage::

        device = VirtualDevice('myhost')
        daemon = Telnetd('localhost', 1234, device)
        device.add_command('ls', 'ok', prompt = True)
        device.add_command('exit', daemon.exit_command)
        daemon.start() # Start the server.
        daemon.exit()  # Stop the server.
        daemon.join()  # Wait until it terminates.

    @type  host: str
    @param host: The address against whcih the daemon binds.
    @type  port: str
    @param port: The TCP port on which to listen.
    @type  device: VirtualDevice
    @param device: A virtual device instance.
    """

    def __init__(self, host, port, device):
        Process.__init__(self, target = self._run)
        self.host    = host
        self.port    = int(port)
        self.timeout = .5
        self.dbg     = 0
        self.running = False
        self.buf     = ''
        self.socket  = None
        self.conn    = None
        self.device  = device
        self.parent_conn, self.child_conn = Pipe()

    def _dbg(self, level, msg):
        if self.dbg >= level:
            print self.host + ':' + str(self.port), '-',
            print msg

    def _poll_child_process(self):
        if not self.child_conn.poll():
            return False
        if not self.running:
            return False
        try:
            msg = self.child_conn.recv()
        except socket.error, e:
            self.running = False
            return False
        if msg == 'shutdown':
            self.running = False
            self._shutdown_notify()
            return False
        return True

    def _shutdown_notify(self):
        raise NotImplementedError()

    def _run(self):
        raise NotImplementedError()

    def exit(self):
        """
        Stop the daemon without waiting for the thread to terminate.
        """
        self.parent_conn.send('shutdown')

    def exit_command(self, cmd):
        """
        Like exit(), but may be used as a handler in add_command.

        @type  cmd: str
        @param cmd: The command that causes the server to exit.
        """
        self.exit()
        return ''
