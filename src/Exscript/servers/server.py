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
from typing import cast

from ..emulators import VirtualDevice

_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())


# A thread, not a process: on POSIX, forking a program that runs threads may
# deadlock the child.
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

    def __init__(self, host: str, port: int, device: VirtualDevice, encoding: str = 'utf8') -> None:
        """
        Constructor.

        :type  host: str
        :param host: The address against which the daemon binds.
        :type  port: int
        :param port: The TCP port on which to listen; 0 lets start() choose a
            free one.
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
        self.socket: socket.socket | None = None  # set by start()
        self.device = device  # Shared device does not support concurrent connections!
        self.encoding = encoding
        self.to_child, self.to_parent = Pipe()
        self.processes: list[threading.Thread] = []

    def _dbg(self, level: int, msg: str, exc_info: bool | BaseException | None = None) -> None:
        """
        Logs the given message if the debug level (the dbg attribute) is at
        least the given level.
        """
        if level > self.dbg:
            return
        self._logger.debug(msg, exc_info=exc_info)

    def _poll_child_process(self) -> bool:
        """
        Reads a message from the pipe, if one is waiting. The message
        "shutdown" from exit(), or an error while reading, stops the server.

        :return: Whether another message was read while the server runs.
        """
        if not self.to_parent.poll():
            return False
        try:
            msg = self.to_parent.recv()
            self._dbg(1, 'Received command via pipe from parent: %s' % repr(msg))
        except OSError:
            self.running = False
            return False
        if msg == 'shutdown':
            self.running = False
            return False
        if not self.running:
            return False
        return True

    def _handle_connection(self, conn: socket.socket) -> None:
        """
        Talks to the client on the given accepted connection until it
        disconnects or the server stops. Subclasses implement it.

        :raises NotImplementedError: Always, in this base class.
        """
        raise NotImplementedError()

    def _get_server_type(self) -> str:
        """
        Returns the class name in lower case, which names the threads and
        appears in the debug messages.
        """
        return type(self).__name__.lower()

    def _run(self) -> None:
        """
        Accepts connections until the server stops, and talks to each client
        in a new thread. Then waits for these threads and closes the socket.
        """
        self._dbg(1, 'Starting the %s server.' % self._get_server_type())
        self.running = True

        try:
            while self.running:
                self._poll_child_process()
                # Purge finished handlers to void zombie accumulation.
                self.processes = [p for p in self.processes if p.is_alive()]

                # start() sets the socket before the thread runs; the casts
                # are for the type checker.
                r, w, x = select.select([cast(socket.socket, self.socket)], [], [], self.timeout)
                if not r:
                    continue

                conn, addr = cast(socket.socket, self.socket).accept()
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
            cast(socket.socket, self.socket).close()

    def start(self) -> None:
        """
        Starts listening, and then the thread that accepts the connections.
        Clients can connect as soon as this returns. With port 0, the
        operating system chooses a free port; the port attribute has it then.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((self.host, self.port))
            sock.listen(1)
        except OSError:
            sock.close()
            raise
        self.socket = sock
        self.port = sock.getsockname()[1]
        self.name = '%s-%s:%s' % (self._get_server_type(), self.host, self.port)
        self._dbg(1, 'Server bound to: %s:%s' % (self.host, self.port))
        threading.Thread.start(self)

    def exit(self) -> None:
        """
        Stop the daemon without waiting for the thread to terminate.
        """
        self._dbg(1, 'Shutdown the %s server.' % self._get_server_type())
        self.to_child.send('shutdown')

    def exit_command(self, cmd: str) -> str:
        """
        Like exit(), but may be used as a handler in add_command.

        :type  cmd: str
        :param cmd: The command that causes the server to exit.
        :return: An empty string, the response to the command.
        """
        self.exit()
        return ''
