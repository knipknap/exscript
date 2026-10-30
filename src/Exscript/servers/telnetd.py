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

import logging
import select
import socket

from .server import Server

_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())


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

    def __init__(self, host, port, device):
        Server.__init__(self, host, port, device)
        self._logger = _logger

    def _recvline(self, conn, buf):
        while b'\n' not in buf:
            r, w, x = select.select([conn], [], [], self.timeout)
            if not self.running:
                return None, buf
            if not r:
                continue
            data = conn.recv(1024)
            if not data:
                return None, buf  # client disconnected — keep server running
            buf += data.replace(b'\r\n', b'\n').replace(b'\r', b'\n')
        lines = buf.split(b'\n')
        return lines[0].decode(self.encoding) + '\n', b'\n'.join(lines[1:])

    def _handle_connection(self, conn):
        try:
            # send the banner
            conn.send(self.device.init().encode('utf8'))

            # accept commands
            buf = b''
            while self.running:
                line, buf = self._recvline(conn, buf)
                if line is None:
                    break
                response = self.device.do(line)
                if response:
                    conn.send(response.encode('utf8'))
        except (socket.error, EOFError) as err:
            msg = 'Client disappeared: ' + str(err)
            self._dbg(1, msg)
        except Exception as err:
            msg = "%s in connection handler: %s"
            self._dbg(1, msg % (type(err).__name__, str(err)))
        finally:
            conn.close()
