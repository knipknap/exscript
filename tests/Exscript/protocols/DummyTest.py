import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from TransportTest      import TransportTest
from Exscript.emulators import VirtualDevice
from Exscript.protocols import Dummy

class DummyTest(TransportTest):
    CORRELATE = Dummy

    def createTransport(self):
        self.device    = VirtualDevice(self.hostname, echo = True)
        self.transport = Dummy(device = self.device)
        self.banner    = 'Welcome to %s!\n' % self.hostname
        self.prompt    = self.hostname + '> '

        ls_response = '-rw-r--r--  1 sab  nmc    1628 Aug 18 10:02 file'
        self.device.add_command('ls',   ls_response)
        self.device.add_command('df',   'foobar')
        self.device.add_command('exit', '')

    def testConstructor(self):
        self.assert_(isinstance(self.transport, Dummy))

    def testIsDummy(self):
        self.assert_(self.transport.is_dummy())

    def _create_dummy_and_eat_banner(self, device, port = None):
        transport = Dummy(device = device)
        transport.connect(device.hostname, port)
        self.assertEqual(transport.buffer,   '')
        self.assertEqual(transport.response, None)
        transport.expect(re.compile(re.escape(self.banner)))
        self.assertEqual(transport.response, '')
        return transport

    def testDummy(self):
        # Test simple instance with banner.
        transport = Dummy(device = self.device)
        transport.connect('testhost')
        self.assertEqual(transport.buffer,   '')
        self.assertEqual(transport.response, None)
        transport.close()

        # Test login.
        transport = Dummy(device = self.device)
        transport.connect('testhost')
        self.assertEqual(transport.buffer,   '')
        self.assertEqual(transport.response, None)
        transport.login(self.account, flush = False)
        self.assert_(transport.buffer.endswith(self.prompt))
        transport.close()

        # Test login with user prompt.
        device = VirtualDevice(self.hostname,
                               echo       = True,
                               login_type = VirtualDevice.LOGIN_TYPE_USERONLY)
        transport = self._create_dummy_and_eat_banner(device)
        self.assertEqual(transport.buffer, 'User: ')
        transport.login(self.account, flush = False)
        self.assert_(transport.buffer.endswith(self.prompt), repr(transport.buffer))
        transport.close()

        # Test login with password prompt.
        device = VirtualDevice(self.hostname,
                               echo       = True,
                               login_type = VirtualDevice.LOGIN_TYPE_PASSWORDONLY)
        transport = self._create_dummy_and_eat_banner(device)
        self.assertEqual(transport.buffer, 'Password: ')
        transport.login(self.account, flush = False)
        self.assert_(transport.buffer.endswith(self.prompt))
        transport.close()

        # Test login without user/password prompt.
        device = VirtualDevice(self.hostname,
                               echo       = True,
                               login_type = VirtualDevice.LOGIN_TYPE_NONE)
        transport = self._create_dummy_and_eat_banner(device)
        self.assertEqual(transport.buffer, self.prompt)
        transport.close()

        # Test login with user prompt and wait parameter.
        device = VirtualDevice(self.hostname,
                               echo       = True,
                               login_type = VirtualDevice.LOGIN_TYPE_USERONLY)
        transport = self._create_dummy_and_eat_banner(device)
        self.assertEqual(transport.buffer, 'User: ')
        transport.login(self.account)
        self.assertEqual(transport.buffer,   '')
        self.assertEqual(transport.response, self.user + '\r')
        transport.close()

        # Test login with password prompt and wait parameter.
        device = VirtualDevice(self.hostname,
                               echo       = True,
                               login_type = VirtualDevice.LOGIN_TYPE_PASSWORDONLY)
        transport = self._create_dummy_and_eat_banner(device)
        self.assertEqual(transport.buffer, 'Password: ')
        transport.login(self.account)
        self.assertEqual(transport.buffer,   '')
        self.assertEqual(transport.response, self.password + '\r')
        transport.close()

        # Test login with port number.
        transport = self._create_dummy_and_eat_banner(device, 1234)
        self.assertEqual(transport.buffer, 'Password: ')
        transport.login(self.account)
        self.assertEqual(transport.buffer,   '')
        self.assertEqual(transport.response, self.password + '\r')
        transport.close()

        # Test a custom response.
        device = VirtualDevice(self.hostname,
                               echo       = True,
                               login_type = VirtualDevice.LOGIN_TYPE_NONE)
        transport = Dummy(device = device)
        command   = re.compile(r'testcommand')
        response  = 'hello world\r\n%s> ' % self.hostname
        device.add_command(command, response, prompt = False)
        transport.set_prompt(re.compile(r'> $'))
        transport.connect('testhost')
        transport.expect(re.compile(re.escape(self.banner)))
        self.assertEqual(transport.response, '')
        self.assertEqual(transport.buffer, self.prompt)
        transport.expect_prompt()
        self.assertEqual(transport.buffer,   '')
        self.assertEqual(transport.response, self.hostname)
        transport.execute('testcommand')
        expected = 'testcommand\rhello world\r\n' + self.hostname
        self.assertEqual(transport.response, expected)
        self.assertEqual(transport.buffer,   '')
        transport.close()

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(DummyTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
