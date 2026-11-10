"""Tests for the functions of the Exscript.protocols package."""

import os
import unittest

import Exscript.protocols
from Exscript import Account, Host
from Exscript.emulators import VirtualDevice
from Exscript.protocols import (
    SSH2,
    Dummy,
    Netconf,
    Telnet,
    connect,
    create_protocol,
    get_protocol_from_name,
    prepare,
)
from Exscript.servers import Telnetd

PSEUDODEV = os.path.join(os.path.dirname(__file__), 'pseudodev.py')


class ProtocolsTest(unittest.TestCase):
    CORRELATE = Exscript.protocols

    def startServer(self):
        device = VirtualDevice('r1', echo=True)
        device.add_command('show version', 'Version 1.0')
        daemon = Telnetd('127.0.0.1', 0, device)
        daemon.timeout = 0.05
        daemon.start()
        self.addCleanup(daemon.join)
        self.addCleanup(daemon.exit)
        return daemon.port

    def testGetProtocolFromName(self):
        classes = {
            'dummy': Dummy,
            'pseudo': Dummy,
            'telnet': Telnet,
            'ssh': SSH2,
            'ssh2': SSH2,
            'netconf': Netconf,
        }
        for name, cls in classes.items():
            self.assertIs(get_protocol_from_name(name), cls)
        self.assertRaisesRegex(
            ValueError, 'Unsupported protocol "rlogin"', get_protocol_from_name, 'rlogin'
        )

    def testCreateProtocol(self):
        conn = create_protocol('telnet', timeout=7, driver='ios')
        self.assertIsInstance(conn, Telnet)
        self.assertEqual(conn.get_timeout(), 7)
        self.assertEqual(conn.get_driver().name, 'ios')
        self.assertFalse(conn.connected)
        self.assertRaisesRegex(
            ValueError, 'Unsupported protocol "rlogin"', create_protocol, 'rlogin'
        )

    def testPrepare(self):
        conn = prepare('telnet://router1:2323', timeout=7)
        self.assertIsInstance(conn, Telnet)
        self.assertEqual(conn.get_timeout(), 7)
        self.assertFalse(conn.connected)
        self.assertIsInstance(prepare('router1'), SSH2)  # the default protocol
        self.assertIsInstance(prepare('router1', default_protocol='telnet'), Telnet)
        self.assertIsInstance(prepare(Host('netconf://router1')), Netconf)
        self.assertRaisesRegex(ValueError, 'Unsupported protocol "rlogin"', prepare, 'rlogin://r1')

    def testPseudoDevice(self):
        # The address of a pseudo host is a file with the commands of the device.
        host = Host('pseudo://' + PSEUDODEV)
        host.set_account(Account('admin', 'secret', needs_lock=False))
        self.assertIsInstance(prepare(host), Dummy)
        conn = connect(host)
        self.addCleanup(conn.close, force=True)
        self.assertTrue(conn.is_app_authenticated())
        conn.execute('show version')
        self.assertIn('Cisco Internetwork Operating System Software', conn.response)

    def testConnectWithLogin(self):
        port = self.startServer()
        conn = connect(f'telnet://admin:secret@127.0.0.1:{port}', timeout=2, connect_rate_limit=0)
        self.addCleanup(conn.close, force=True)
        self.assertTrue(conn.connected)
        self.assertTrue(conn.is_app_authenticated())
        conn.execute('show version')
        self.assertIn('Version 1.0', conn.response)

    def testConnectWithoutLogin(self):
        port = self.startServer()
        host = Host(f'127.0.0.1:{port}', default_protocol='telnet')
        conn = connect(host, timeout=2, connect_rate_limit=0)
        self.addCleanup(conn.close, force=True)
        self.assertIsInstance(conn, Telnet)
        self.assertTrue(conn.connected)
        self.assertFalse(conn.is_app_authenticated())
        conn.login(Account('admin', 'secret', needs_lock=False))
        self.assertTrue(conn.is_app_authorized())

    def testConnectWithTheAccountOfTheHost(self):
        port = self.startServer()
        host = Host(f'telnet://127.0.0.1:{port}')
        host.set_account(Account('admin', 'secret', needs_lock=False))
        conn = connect(host, timeout=2, connect_rate_limit=0)
        self.addCleanup(conn.close, force=True)
        self.assertTrue(conn.is_app_authenticated())


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(ProtocolsTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
