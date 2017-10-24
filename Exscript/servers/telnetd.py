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
from __future__ import absolute_import, print_function
import select
from copy import deepcopy
from .server import Server


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
        while not b'\n' in self.buf:
            r, w, x = select.select([conn], [], [], self.timeout)
            if not self.running:
                return None
            if not r:
                continue
            buf = conn.recv(1024)
            if not buf:
                self.running = False
                return None
            self.buf += buf.replace(b'\r\n', b'\n').replace(b'\r', b'\n')
        lines = self.buf.split(b'\n')
        self.buf = b'\n'.join(lines[1:])
        return lines[0].decode(self.encoding) + '\n'

    def _handle_connection(self, conn):
        try:
            device = deepcopy(self.device)
            conn.send(device.init().encode('utf8'))

            while self.running:
                line = self._recvline(conn)
                if not line:
                    continue
                response = self.device.do(line)
                if response:
                    conn.send(response.encode('utf8'))
        except Exception as err:
            self._dbg("_handle_connection(): ", err)
        finally:
            conn.close()
