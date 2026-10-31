import re
import unittest

from Exscript import Account
from Exscript.emulators import VirtualDevice
from Exscript.protocols import Dummy
from Exscript.protocols.exception import InvalidCommandException

from .ProtocolTest import ProtocolTest


class DummyTest(ProtocolTest):
    CORRELATE = Dummy

    def createProtocol(self):
        self.protocol = Dummy(device=self.device, timeout=1, debug=5)

    def testConstructor(self):
        self.assertIsInstance(self.protocol, Dummy)

    def testIsDummy(self):
        self.assertTrue(self.protocol.is_dummy())

    def _create_dummy_and_eat_banner(self, device, port=None):
        protocol = Dummy(device=device)
        protocol.connect(device.hostname, port)
        self.assertEqual(str(protocol._buffer), '')
        self.assertEqual(protocol.response, None)
        protocol.expect(re.compile(re.escape(self.banner)))
        self.assertEqual(protocol.response, '')
        return protocol

    def testDummy(self):
        # Test simple instance with banner.
        protocol = Dummy(device=self.device)
        protocol.connect('testhost')
        self.assertEqual(str(protocol._buffer), '')
        self.assertEqual(protocol.response, None)
        protocol.close()

        # Test login.
        protocol = Dummy(device=self.device)
        protocol.connect('testhost')
        self.assertEqual(str(protocol._buffer), '')
        self.assertEqual(protocol.response, None)
        protocol.login(self.account, flush=False)
        self.assertEqual(protocol._buffer.tail(len(self.prompt)), self.prompt)
        protocol.close()

        # Test login with user prompt.
        device = VirtualDevice(
            self.hostname, echo=True, login_type=VirtualDevice.LOGIN_TYPE_USERONLY
        )
        protocol = self._create_dummy_and_eat_banner(device)
        self.assertEqual(str(protocol._buffer), 'User: ')
        protocol.login(self.account, flush=False)
        self.assertEqual(protocol._buffer.tail(len(self.prompt)), self.prompt)
        protocol.close()

        # Test login with password prompt.
        device = VirtualDevice(
            self.hostname, echo=True, login_type=VirtualDevice.LOGIN_TYPE_PASSWORDONLY
        )
        protocol = self._create_dummy_and_eat_banner(device)
        self.assertEqual(str(protocol._buffer), 'Password: ')
        protocol.login(self.account, flush=False)
        self.assertEqual(protocol._buffer.tail(len(self.prompt)), self.prompt)
        protocol.close()

        # Test login without user/password prompt.
        device = VirtualDevice(self.hostname, echo=True, login_type=VirtualDevice.LOGIN_TYPE_NONE)
        protocol = self._create_dummy_and_eat_banner(device)
        self.assertEqual(str(protocol._buffer), self.prompt)
        protocol.close()

        # Test login with user prompt and wait parameter.
        device = VirtualDevice(
            self.hostname, echo=True, login_type=VirtualDevice.LOGIN_TYPE_USERONLY
        )
        protocol = self._create_dummy_and_eat_banner(device)
        self.assertEqual(str(protocol._buffer), 'User: ')
        protocol.login(self.account)
        self.assertEqual(str(protocol._buffer), '')
        self.assertEqual(protocol.response, self.user)
        protocol.close()

        # Test login with password prompt and wait parameter.
        device = VirtualDevice(
            self.hostname, echo=True, login_type=VirtualDevice.LOGIN_TYPE_PASSWORDONLY
        )
        protocol = self._create_dummy_and_eat_banner(device)
        self.assertEqual(str(protocol._buffer), 'Password: ')
        protocol.login(self.account)
        self.assertEqual(str(protocol._buffer), '')
        self.assertEqual(protocol.response, self.password)
        protocol.close()

        # Test login with port number.
        protocol = self._create_dummy_and_eat_banner(device, 1234)
        self.assertEqual(str(protocol._buffer), 'Password: ')
        protocol.login(self.account)
        self.assertEqual(str(protocol._buffer), '')
        self.assertEqual(protocol.response, self.password)
        protocol.close()

        # Test a custom response.
        device = VirtualDevice(self.hostname, echo=True, login_type=VirtualDevice.LOGIN_TYPE_NONE)
        protocol = Dummy(device=device)
        command = re.compile(r'testcommand')
        response = 'hello world\r\n%s> ' % self.hostname
        device.add_command(command, response, prompt=False)
        protocol.set_prompt(re.compile(r'> $'))
        protocol.connect('testhost')
        protocol.expect(re.compile(re.escape(self.banner)))
        self.assertEqual(protocol.response, '')
        self.assertEqual(str(protocol._buffer), self.prompt)
        protocol.expect_prompt()
        self.assertEqual(str(protocol._buffer), '')
        self.assertEqual(protocol.response, self.hostname)
        protocol.execute('testcommand')
        expected = 'testcommand\rhello world\r\n' + self.hostname
        self.assertEqual(protocol.response, expected)
        self.assertEqual(str(protocol._buffer), '')
        protocol.close()


class SecretHygieneTest(unittest.TestCase):
    PASSWORD = 'S3cr3t-P@ss'

    def testDebugLogRedactsPassword(self):
        conn = Dummy(device=VirtualDevice('r1', echo=False, strict=False), debug=4)
        with self.assertLogs('Exscript.protocols', level='DEBUG') as logs:
            conn.connect('r1')
            conn.login(Account('admin', self.PASSWORD, needs_lock=False))
        conn.close(force=True)
        self.assertIn('Sending: <secret>', '\n'.join(logs.output))
        self.assertEqual([line for line in logs.output if self.PASSWORD in line], [])

    def testErrorMessageShowsOnlyTheErrorLine(self):
        device = VirtualDevice('r1', echo=False, strict=False)
        device.add_command('show run', 'enable secret PRIVATE\r\n% Invalid input detected')
        conn = Dummy(device=device)
        conn.connect('r1')
        conn.login(Account('admin', self.PASSWORD, needs_lock=False))
        with self.assertRaises(InvalidCommandException) as cm:
            conn.execute('show run')
        self.assertEqual(
            str(cm.exception), 'Error in the response from the device: % Invalid input detected'
        )
        self.assertIn('PRIVATE', conn.response)
        conn.close(force=True)


def suite():
    loader = unittest.TestLoader()
    return unittest.TestSuite(
        [
            loader.loadTestsFromTestCase(DummyTest),
            loader.loadTestsFromTestCase(SecretHygieneTest),
        ]
    )


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
