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
A Telnet server.
"""
import socket
import select
from Exscript.servers.Server import Server

class Telnetd(Server):
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

    def _recvline(self):
        while not '\n' in self.buf:
            self._poll_child_process()
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

    def _shutdown_notify(self):
        try:
            self.conn.send('Server is shutting down.\n')
        except Exception:
            pass

    def _run(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        self.socket.listen(1)
        self.running = True

        while self.running:
            self._poll_child_process()

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
            except socket.error:
                pass # network error
            finally:
                self.conn.close()

        self.socket.close()
