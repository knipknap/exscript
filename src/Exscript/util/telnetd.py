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
A very simple Telnet server for emulating a device.
"""
import socket, select
from multiprocessing    import Process, Pipe
from Exscript.emulators import VirtualDevice

class Telnetd(Process):
    """
    A Telnet server. Usage::

        device = VirtualDevice('myhost')
        daemon = Telnetd('localhost', 1234, device)
        device.add_command('ls', 'ok', prompt = True)
        device.add_command('exit', daemon.exit_command)
        daemon.start() # Start the server.
        daemon.exit()  # Stop the server.
        daemon.join()  # Wait until it terminates.
    """

    def __init__(self, host, port, device):
        Process.__init__(self, target = self._run)
        self.host    = host
        self.port    = int(port)
        self.timeout = 1
        self.running = False
        self.buf     = ''
        self.socket  = None
        self.conn    = None
        self.device  = device
        self.parent_conn, self.child_conn = Pipe()

    def _recvline(self):
        while not '\n' in self.buf:
            self._check_pipe()
            r, w, x = select.select([self.conn], [], [], self.timeout)
            if not self.running:
                return None
            if not r:
                continue
            buf = self.conn.recv(1024)
            if not buf:
                self.running = False
                return None
            self.buf += buf.replace('\r\n', '\n').replace('\r', '\n')
        lines    = self.buf.split('\n')
        self.buf = '\n'.join(lines[1:])
        return lines[0] + '\n'

    def _check_pipe(self):
        if not self.child_conn.poll():
            return
        try:
            msg = self.child_conn.recv()
            if msg == 'shutdown':
                self._exit()
        except socket.error, e:
            self.running = False

    def _exit(self):
        if self.conn:
            self.conn.send('Server is shutting down.\n')
        self.running = False

    def _run(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        self.socket.listen(1)
        self.running = True

        while self.running:
            self._check_pipe()
            r, w, x = select.select([self.socket], [], [], self.timeout)
            if not r:
                continue

            self.conn, addr = self.socket.accept()

            try:
                self.conn.send(self.device.init())

                while self.running:
                    line = self._recvline()
                    if not line:
                        continue
                    response = self.device.do(line)
                    if response:
                        self.conn.send(response)
            except socket.error, e:
                pass # network error
            finally:
                self.conn.close()

        self.socket.close()

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
