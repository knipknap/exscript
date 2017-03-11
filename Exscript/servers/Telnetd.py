# 
# Copyright (C) 2010-2017 Samuel Abels
# The MIT License (MIT)
# 
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
A Telnet server.
"""
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

    def _recvline(self, conn):
        while not '\n' in self.buf:
            self._poll_child_process()
            r, w, x = select.select([conn], [], [], self.timeout)
            if not self.running:
                return None
            if not r:
                continue
            buf = conn.recv(1024)
            if not buf:
                self.running = False
                return None
            self.buf += buf.replace('\r\n', '\n').replace('\r', '\n')
        lines    = self.buf.split('\n')
        self.buf = '\n'.join(lines[1:])
        return lines[0] + '\n'

    def _shutdown_notify(self, conn):
        try:
            conn.send('Server is shutting down.\n')
        except Exception:
            pass

    def _handle_connection(self, conn):
        conn.send(self.device.init())

        while self.running:
            line = self._recvline(conn)
            if not line:
                continue
            response = self.device.do(line)
            if response:
                conn.send(response)
