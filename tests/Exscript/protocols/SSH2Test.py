import os
import socket
import tempfile
import threading
import unittest
from unittest import mock

import paramiko

from Exscript import PrivateKey
from Exscript.protocols import SSH2, Netconf
from Exscript.protocols.ssh2 import _prefer_key_type
from Exscript.servers import SSHd, sshd

from .ProtocolTest import ProtocolTest

keyfile = os.path.join(os.path.dirname(__file__), 'id_rsa')
key = PrivateKey.from_file(keyfile)
HOST = '127.0.0.1'


class SSH2Test(ProtocolTest):
    CORRELATE = SSH2

    def createDaemon(self):
        self.daemon = SSHd(self.hostname, self.port, self.device, key=key)
        self.daemon.dbg = 5

    def createProtocol(self):
        self.protocol = SSH2(timeout=1, debug=5, verify_fingerprint=False)

    def testConstructor(self):
        self.assertIsInstance(self.protocol, SSH2)

    def testGetRemoteVersion(self):
        self.assertEqual(self.protocol.get_remote_version(), None)
        self.doConnect()
        self.assertEqual(self.protocol.get_remote_version(), sshd.local_version)

    def testLogin(self):
        self.assertRaises(IOError, ProtocolTest.testLogin, self)

    def testAuthenticate(self):
        self.assertRaises(IOError, ProtocolTest.testAuthenticate, self)


class KeyServer:
    """Completes the SSH key exchange with its host keys; nothing else."""

    def __init__(self, test, *keys):
        self.keys = keys
        self._transports = []
        self._closing = threading.Event()
        self._listener = socket.create_server((HOST, 0))
        self._listener.settimeout(0.1)
        self.port = self._listener.getsockname()[1]
        self._thread = threading.Thread(target=self._accept, daemon=True)
        self._thread.start()
        test.addCleanup(self.close)

    def _accept(self):
        while not self._closing.is_set():
            try:
                sock, _ = self._listener.accept()
            except TimeoutError:
                continue
            transport = paramiko.Transport(sock)
            for host_key in self.keys:
                transport.add_server_key(host_key)
            self._transports.append(transport)
            # With an event, the key exchange runs in the transport's thread, and the
            # transport stays open until the client or close() closes it.
            transport.start_server(event=threading.Event(), server=paramiko.ServerInterface())

    def close(self):
        self._closing.set()
        self._thread.join()
        self._listener.close()
        for transport in self._transports:
            transport.close()


class HostKeyTest(unittest.TestCase):
    """The host key is checked against known_hosts before any credentials are sent."""

    server_key = paramiko.RSAKey(filename=keyfile)
    other_key = paramiko.RSAKey.generate(1024)

    def setUp(self):
        self.server = KeyServer(self, self.server_key)
        self.name = f'[{HOST}]:{self.server.port}'
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        self.known_hosts = os.path.join(tmpdir.name, 'known_hosts')

    def writeKnownHosts(self, *entries):
        with open(self.known_hosts, 'w') as fp:
            for name, host_key in entries:
                fp.write(f'{name} {host_key.get_name()} {host_key.get_base64()}\n')

    def connect(self, conn=None, cls=SSH2, **kwargs):
        if conn is None:
            conn = cls(timeout=1, connect_rate_limit=0, known_hosts=self.known_hosts, **kwargs)
            self.addCleanup(conn.close, force=True)
        conn.connect(HOST, self.server.port)
        return conn

    def testUnknownHostIsRejectedByDefault(self):
        for cls in SSH2, Netconf:
            with self.assertRaisesRegex(paramiko.SSHException, 'Rejecting unknown ssh-rsa'):
                self.connect(cls=cls)

    def testKnownHostIsAccepted(self):
        self.writeKnownHosts((self.name, self.server_key))
        self.assertTrue(self.connect().connected)

    def testHashedKnownHostIsAccepted(self):
        self.writeKnownHosts((paramiko.HostKeys.hash_host(self.name), self.server_key))
        self.assertTrue(self.connect().connected)

    def testChangedKeyIsRejected(self):
        self.writeKnownHosts((self.name, self.other_key))
        for policy in 'reject', 'warn', 'auto-add':
            with self.assertRaises(paramiko.BadHostKeyException):
                self.connect(host_key_policy=policy)
        self.connect(verify_fingerprint=False)

    def testDefaultKnownHostsFile(self):
        home = os.path.dirname(self.known_hosts)
        os.mkdir(os.path.join(home, '.ssh'))
        self.known_hosts = os.path.join(home, '.ssh', 'known_hosts')
        self.writeKnownHosts((self.name, self.other_key))
        with mock.patch.dict(os.environ, {'HOME': home, 'USERPROFILE': home}):
            conn = SSH2(timeout=1, connect_rate_limit=0)
            self.addCleanup(conn.close, force=True)
            with self.assertRaises(paramiko.BadHostKeyException):
                self.connect(conn)

    def testWarnPolicyPinsTheKey(self):
        with self.assertLogs('Exscript.protocols.ssh2', 'WARNING') as logs:
            conn = self.connect(host_key_policy='warn')
        self.assertIn(self.name, logs.output[0])
        self.assertFalse(os.path.exists(self.known_hosts))

        # A reconnect of the same object must present the same key.
        conn.close(force=True)
        self.server.keys = (self.other_key,)
        with self.assertRaises(paramiko.BadHostKeyException):
            self.connect(conn)

    def testAutoAddPolicyAppendsToKnownHosts(self):
        with open(self.known_hosts, 'w') as fp:
            fp.write(f'192.0.2.1 {self.other_key.get_name()} {self.other_key.get_base64()}')
        self.connect(host_key_policy='auto-add')
        known = paramiko.HostKeys(self.known_hosts)
        self.assertEqual(known.lookup('192.0.2.1')['ssh-rsa'], self.other_key)
        self.assertEqual(known.lookup(self.name)['ssh-rsa'], self.server_key)
        self.connect()  # now known

    def testKnownKeyTypeIsPreferred(self):
        self.server.keys = (paramiko.ECDSAKey.generate(), self.server_key)
        self.writeKnownHosts((self.name, self.server_key))
        self.connect()

    def testPreferKeyType(self):
        options = mock.Mock(key_types=('ssh-ed25519', 'rsa-sha2-512', 'rsa-sha2-256'))
        _prefer_key_type(options, 'ssh-rsa')
        self.assertEqual(options.key_types, ['rsa-sha2-512', 'ssh-ed25519', 'rsa-sha2-256'])
        _prefer_key_type(options, 'ssh-dss')  # not offered: unchanged
        self.assertEqual(options.key_types, ['rsa-sha2-512', 'ssh-ed25519', 'rsa-sha2-256'])

    def testInvalidPolicy(self):
        self.assertRaises(ValueError, SSH2, host_key_policy='yes')


def suite():
    loader = unittest.TestLoader()
    return unittest.TestSuite(
        [
            loader.loadTestsFromTestCase(SSH2Test),
            loader.loadTestsFromTestCase(HostKeyTest),
        ]
    )


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
