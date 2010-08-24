import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from TransportTest      import TransportTest
from Exscript.protocols import Dummy

class DummyTest(TransportTest):
    CORRELATE = Dummy

    def createTransport(self):
        self.transport = Dummy(echo = 1)

    def testConstructor(self):
        self.assert_(isinstance(self.transport, Dummy))

    def testIsDummy(self):
        self.assert_(self.transport.is_dummy())

    def testAddCommandHandler(self):
        self.doAuthenticate(wait = True)

        self.transport.execute('blah')
        self.assertEqual(self.transport.response, 'blah\r')

        # Responds using a string.
        self.transport.add_command_handler('blah', 'foobar\r\ntest>')
        self.transport.execute('blah')
        self.assertEqual(self.transport.response, 'blah\r\nfoobar\r')

        # Responds using a function.
        say_hello = lambda cmd: cmd.strip() + ' world\r\ntest>'
        self.transport.add_command_handler('hello', say_hello)
        self.transport.execute('hello')
        self.assertEqual(self.transport.response, 'hello\r\nhello world\r')

    def testLoadCommandHandlerFromFile(self):
        testdir   = os.path.join(os.path.dirname(__file__), '..', '..')
        dirname   = os.path.join(testdir, 'templates', 'iosdummy')
        filename  = os.path.join(dirname, 'pseudodev.py')
        transport = Dummy(banner = 'blah', strict = True)
        transport.load_command_handler_from_file(filename)
        transport.connect('testhost')
        transport.authenticate('user', 'password')
        transport.execute('show version')
        self.assert_('cisco 12416' in transport.response)
        transport.execute('show diag 0')
        self.assert_('SLOT 0' in transport.response, repr(transport.response))

        # The following must raise because of the strict = True argument
        # above. The reason is that the command "show something" is not
        # known.
        self.assertRaises(Exception, transport.execute, 'show something')
        transport.close()

    def testGuessOs(self):
        self.assertEqual('unknown', self.transport.guess_os())
        self.transport.connect(self.host)
        self.assertEqual('ios', self.transport.guess_os())
        self.transport.authenticate(self.user, self.password, wait = True)
        self.assertEqual('ios', self.transport.guess_os())

    def testDummy(self):
        # Test simple instance with banner.
        transport = Dummy(banner = 'blah')
        transport.connect('testhost')
        self.assert_(transport.buffer == 'blah\r\nUsername: ')
        self.assert_(transport.response is None)
        transport.close()

        # Test login.
        transport = Dummy()
        transport.connect('testhost')
        self.assert_(transport.buffer == 'Username: ')
        self.assert_(transport.response is None)
        transport.authenticate('sab', 'test')
        self.assert_(transport.buffer.endswith('testhost:0> '))
        transport.close()

        # Test login with user prompt.
        transport = Dummy(login_type = Dummy.LOGIN_TYPE_USERONLY)
        transport.connect('testhost')
        self.assert_(transport.buffer == 'Username: ')
        self.assert_(transport.response is None)
        transport.authenticate('sab', '')
        self.assert_(transport.buffer.endswith('testhost:0> '))
        transport.close()

        # Test login with password prompt.
        transport = Dummy(login_type = Dummy.LOGIN_TYPE_PASSWORDONLY)
        transport.connect('testhost')
        self.assert_(transport.buffer == 'Password: ')
        self.assert_(transport.response is None)
        transport.authenticate(None, 'test')
        self.assert_(transport.buffer.endswith('testhost:0> '))
        transport.close()

        # Test login without user/password prompt.
        transport = Dummy(login_type = Dummy.LOGIN_TYPE_NONE)
        transport.connect('testhost')
        self.assert_(transport.buffer == 'testhost:0> ')
        self.assert_(transport.response is None)
        transport.close()

        # Test login with user prompt and wait parameter.
        transport = Dummy(login_type = Dummy.LOGIN_TYPE_USERONLY)
        transport.connect('testhost')
        self.assertEqual(transport.buffer,  'Username: ')
        self.assertEqual(transport.response, None)
        transport.authenticate('sab', '', wait = True)
        self.assertEqual(transport.buffer,   '')
        self.assertEqual(transport.response, 'sab\r')
        transport.close()

        # Test login with password prompt and wait parameter.
        transport = Dummy(login_type = Dummy.LOGIN_TYPE_PASSWORDONLY)
        transport.connect('testhost')
        self.assertEqual(transport.buffer,  'Password: ')
        self.assertEqual(transport.response, None)
        transport.authenticate(None, 'test', wait = True)
        self.assertEqual(transport.buffer,   '')
        self.assertEqual(transport.response, 'test\r')
        transport.close()

        # Test login with port number.
        transport = Dummy()
        transport.connect('testhost', 1234)
        self.assertEqual(transport.buffer,   'Username: ')
        self.assertEqual(transport.response, None)
        transport.authenticate('sab', 'test', wait = True)
        self.assertEqual(transport.buffer,   '')
        self.assertEqual(transport.response, 'test\r')
        transport.close()

        # Test a custom response.
        transport = Dummy(login_type = Dummy.LOGIN_TYPE_NONE)
        command   = re.compile(r'testcommand')
        response  = 'hello world\r\ntesthost:0> '
        transport.add_command_handler(command, response)
        transport.set_prompt(re.compile(r'> $'))
        transport.connect('testhost')
        self.assertEqual(transport.buffer,   'testhost:0> ')
        self.assertEqual(transport.response, None)
        transport.expect_prompt()
        self.assertEqual(transport.buffer,   '')
        self.assertEqual(transport.response, 'testhost:0')
        transport.execute('testcommand')
        expected = 'testcommand\r\nhello world\r\ntesthost:0'
        self.assertEqual(transport.response, expected)
        self.assertEqual(transport.buffer,   '')
        transport.close()

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(DummyTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
