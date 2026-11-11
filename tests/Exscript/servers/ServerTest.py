import errno
import gc
import re
import socket
import types
import unittest
import unittest.mock
import warnings

from protocols.listener import listen

from Exscript import Account
from Exscript.emulators import VirtualDevice
from Exscript.servers.server import Server


class ServerTest(unittest.TestCase):
    CORRELATE = Server

    def setUp(self):
        self.host = 'localhost'
        self.port = 0  # start() chooses a free port
        self.device = VirtualDevice(self.host, echo=False)
        self.daemon = Server(self.host, self.port, self.device)
        self.device.set_prompt(self.host + ':' + str(self.port) + '> ')

    def tearDown(self):
        if self.daemon:
            self.daemon.exit()
        if self.daemon.__class__ != Server:
            self.daemon.join()

    def _create_daemon(self):
        raise NotImplementedError()

    def _create_client(self):
        raise NotImplementedError()

    def _add_commands(self):
        self.device.add_command('exit', self.daemon.exit_command)
        self.device.add_command('ls', 'ok1')
        self.device.add_command('ll', 'ok2\nfoobar:1>', prompt=False)
        self.device.add_command('.+', 'Unknown command.')

    def testConstructor(self):
        # Test can not work on the abstract base.
        if self.daemon.__class__ == Server:
            return
        self._create_daemon()
        self.daemon.start()

    def testStart(self):
        # Test can not work on the abstract base.
        if self.daemon.__class__ == Server:
            return
        self._create_daemon()
        self._add_commands()
        self.daemon.start()

        client = self._create_client()
        client.set_prompt(re.compile(r'\w+:\d+> ?'))
        client.connect(self.host, self.daemon.port)
        client.login(Account('user', 'password'))
        client.execute('ls')
        self.assertEqual(client.response, 'ok1\n')
        client.execute('ll')
        self.assertEqual(client.response, 'ok2\n')
        client.send('exit\r')

    def testExitCommand(self):
        pass  # tested in testExit()

    def testExit(self):
        # Test can not work on the abstract base.
        if self.daemon.__class__ == Server:
            return
        self.testStart()
        # Since testStart() sent an "exit" command to the server,
        # it should be shutting down even without us calling
        # self.daemon.exit().
        self.daemon.join()
        self.testConstructor()


class ServerInternalsTest(unittest.TestCase):
    """The parts of the base class that need no client."""

    def setUp(self):
        self.server = Server('127.0.0.1', 0, VirtualDevice('r1'))
        self.addCleanup(self.server.to_parent.close)
        self.addCleanup(self.server.to_child.close)

    def testPollChildProcess(self):
        self.server.running = True
        self.assertFalse(self.server._poll_child_process())  # no message
        self.server.to_child.send('ping')
        self.assertTrue(self.server._poll_child_process())
        self.assertTrue(self.server.running)
        self.server.to_child.send('shutdown')
        self.assertFalse(self.server._poll_child_process())
        self.assertFalse(self.server.running)
        self.server.to_child.send('ping')
        self.assertFalse(self.server._poll_child_process())  # not running

    def testPollChildProcessWithBrokenPipe(self):
        self.server.running = True
        self.server.to_child.send('ping')
        with unittest.mock.patch.object(self.server.to_parent, 'recv', side_effect=OSError):
            self.assertFalse(self.server._poll_child_process())
        self.assertFalse(self.server.running)

    def testHandleConnectionIsAbstract(self):
        self.assertRaises(NotImplementedError, self.server._handle_connection, None)

    def testStartOnAPortInUse(self):
        with listen() as listener:
            server = Server('127.0.0.1', listener.getsockname()[1], self.server.device)
            self.addCleanup(server.to_parent.close)
            self.addCleanup(server.to_child.close)
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter('always', ResourceWarning)
                self.assertRaises(OSError, server.start)
                gc.collect()
        self.assertEqual([str(w.message) for w in caught], [])  # the socket was closed
        self.assertIsNone(server.socket)
        self.assertFalse(server.is_alive())

    def start(self, port):
        server = Server('127.0.0.1', port, self.server.device)
        self.addCleanup(server.to_parent.close)
        self.addCleanup(server.to_child.close)
        server.start()
        self.addCleanup(server.join)
        self.addCleanup(server.exit)
        return server

    def testReuseOfTheAddress(self):
        # Only a fixed port is reused, so that a restarted server can take it at once; port 0
        # gets a free port anyway.
        server = self.start(0)
        self.assertFalse(server.socket.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR))
        server.exit()
        server.join()
        restarted = self.start(server.port)
        self.assertTrue(restarted.socket.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR))

    def testFreePortInUse(self):
        # E.g. on WSL, which forwards the port to its Windows host, where it may be in use:
        # start() tries another free port, but not forever.
        class InUse(socket.socket):
            def listen(self, *args):
                raise OSError(errno.EADDRINUSE, 'Address already in use')

        module = types.SimpleNamespace(**vars(socket))
        with unittest.mock.patch('Exscript.servers.server.socket', module):
            module.socket = unittest.mock.Mock(side_effect=lambda *args: InUse())
            self.assertRaises(OSError, self.start, 0)
            self.assertGreater(module.socket.call_count, 1)
            module.socket = unittest.mock.Mock(side_effect=[InUse(), socket.socket()])
            server = self.start(0)
        self.assertEqual(module.socket.call_count, 2)
        self.assertTrue(server.is_alive())


def suite():
    loader = unittest.TestLoader()
    return unittest.TestSuite(
        [
            loader.loadTestsFromTestCase(ServerTest),
            loader.loadTestsFromTestCase(ServerInternalsTest),
        ]
    )


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
