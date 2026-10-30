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
Base class for all servers.
"""

import logging
import select
import socket
import threading
from multiprocessing import Pipe

_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())


# This formerly was derived from multiprocessing.Process but as POSIX Python
# does not support child processes in threaded environments/apps, we had to
# switch to threaded servers too. This will hopefully add more stability to the
# test suite.
class Server(threading.Thread):
    """
    Base class of the Telnet and SSH servers. Servers are intended to be
    used for tests and attempt to emulate a device using the behavior of
    the associated :class:`Exscript.emulators.VirtualDevice`. Sample usage::

        device = VirtualDevice('myhost')
        daemon = Telnetd('localhost', 1234, device)
        device.add_command('ls', 'ok', prompt = True)
        device.add_command('exit', daemon.exit_command)
        daemon.start() # Start the server.
        daemon.exit()  # Stop the server.
        daemon.join()  # Wait until it terminates.
    """

    def __init__(self, host, port, device, encoding='utf8'):
        """
        Constructor.

        :type  host: str
        :param host: The address against which the daemon binds.
        :type  port: int
        :param port: The TCP port on which to listen.
        :type  device: VirtualDevice
        :param device: A virtual device instance.
        :type encoding: str
        :param encoding: The encoding of data between client and server.
        """
        threading.Thread.__init__(self, target=self._run, daemon=True)
        self._logger = _logger
        self.name = '%s-%s:%s' % (self._get_server_type(), host, port)
        self.host = host
        self.port = int(port)
        self.timeout = 0.5
        self.dbg = 0
        self.running = False
        self.socket = None
        self.device = device  # Shared device does not support concurrent connections!
        self.encoding = encoding
        self.to_child, self.to_parent = Pipe()
        self.processes = []

    def _dbg(self, level, msg, exc_info=None):
        if level > self.dbg:
            return
        self._logger.debug(msg, exc_info=exc_info)

    def _poll_child_process(self):
        if not self.to_parent.poll():
            return False
        try:
            msg = self.to_parent.recv()
            self._dbg(1, 'Received command via pipe from parent: %s' % repr(msg))
        except socket.error:
            self.running = False
            return False
        if msg == 'shutdown':
            self.running = False
            return False
        if not self.running:
            return False
        return True

    def _handle_connection(self, conn):
        raise NotImplementedError()

    def _get_server_type(self):
        return type(self).__name__.lower()

    def _run(self):
        self._dbg(1, 'Starting the %s server.' % self._get_server_type())
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        self.socket.listen(1)
        self.running = True
        self._dbg(1, 'Server bound to: %s:%s' % (self.host, self.port))

        try:
            while self.running:
                self._poll_child_process()
                # Purge finished handlers to void zombie accumulation.
                self.processes = [p for p in self.processes if p.is_alive()]

                r, w, x = select.select([self.socket], [], [], self.timeout)
                if not r:
                    continue

                conn, addr = self.socket.accept()
                self._dbg(1, 'Accepted connection from: %s:%s' % (addr[0], addr[1]))
                proc = threading.Thread(
                    target=self._handle_connection,
                    args=(conn,),
                    name='%s-handler-%s:%s' % (self._get_server_type(), addr[0], addr[1]),
                    daemon=True,
                )
                self.processes.append(proc)
                proc.start()
        finally:
            for proc in self.processes:
                proc.join()
            self.processes = []
            self.socket.close()

    def exit(self):
        """
        Stop the daemon without waiting for the thread to terminate.
        """
        self._dbg(1, 'Shutdown the %s server.' % self._get_server_type())
        self.to_child.send('shutdown')

    def exit_command(self, cmd):
        """
        Like exit(), but may be used as a handler in add_command.

        :type  cmd: str
        :param cmd: The command that causes the server to exit.
        """
        self.exit()
        return ''
