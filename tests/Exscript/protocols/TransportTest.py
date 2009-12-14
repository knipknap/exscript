import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from ConfigParser                 import RawConfigParser
from Exscript.protocols.Transport import Transport, _prompt_re

class TransportTest(unittest.TestCase):
    """
    Since protocols.Transport is abstract, this test is only a base class
    for other protocols. It does not do anything fancy on its own.
    """
    CORRELATE = Transport

    def createTransport(self):
        self.transport = Transport(echo = 0)

    def doAuthenticate(self, wait = True):
        self.transport.connect(self.host)
        self.transport.authenticate(self.user, self.password, wait = wait)

    def doAuthorize(self):
        self.transport.authorize(self.user)

    def setUp(self):
        cfgfile = os.path.join(os.path.dirname(__file__), '..', 'unit_test.cfg')
        cfg     = RawConfigParser()
        cfg.read(cfgfile)
        self.host     = cfg.get('testhost', 'hostname')
        self.user     = cfg.get('testhost', 'user')
        self.password = cfg.get('testhost', 'password')
        self.createTransport()

    def testPrompts(self):
        prompts = [r'[sam123@home ~]$',
                   r'[MyHost-A1]',
                   r'<MyHost-A1>',
                   r'sam@knip:~/Code/exscript$',
                   r'sam@MyHost-X123>',
                   r'sam@MyHost-X123#',
                   r'MyHost-ABC-CDE123>',
                   r'MyHost-A1#',
                   r'S-ABC#',
                   r'0123456-1-1-abc#',
                   r'0123456-1-1-a>',
                   r'MyHost-A1(config)#',
                   r'MyHost-A1(config)>',
                   r'RP/0/RP0/CPU0:A-BC2#',
                   r'FA/0/1/2/3>',
                   r'FA/0/1/2/3(config)>',
                   r'FA/0/1/2/3(config)#',
                   r'admin@s-x-a6.a.bc.de.fg:/# ',
                   r'admin@s-x-a6.a.bc.de.fg:/% ']
        for prompt in prompts:
            if not _prompt_re.search('\n' + prompt):
                self.fail('Prompt %s does not match exactly.' % prompt)
            if not _prompt_re.search('this is a test\r\n' + prompt):
                self.fail('Prompt %s does not match.' % prompt)
            if _prompt_re.search('some text ' + prompt):
                self.fail('Prompt %s matches incorrectly.' % prompt)

    def testConstructor(self):
        self.assert_(isinstance(self.transport, Transport))

    def testCopy(self):
        self.assert_(self.transport == self.transport.__copy__())

    def testDeepcopy(self):
        self.assert_(self.transport == self.transport.__deepcopy__({}))

    def testIsDummy(self):
        self.assert_(self.transport.is_dummy() == False)

    def testSetPrompt(self):
        initial_regex = self.transport.get_prompt()
        self.assert_(hasattr(initial_regex, 'groups'))

        my_re = re.compile(r'test>')
        self.transport.set_prompt(my_re)
        regex = self.transport.get_prompt()
        self.assert_(hasattr(regex, 'groups'))
        self.assert_(regex == my_re)

        self.transport.set_prompt()
        regex = self.transport.get_prompt()
        self.assert_(hasattr(regex, 'groups'))
        self.assert_(regex == initial_regex)

    def testGetPrompt(self):
        pass # Already tested in testSetPrompt()

    def testSetErrorPrompt(self):
        initial_regex = self.transport.get_error_prompt()
        self.assert_(hasattr(initial_regex, 'groups'))

        my_re = re.compile(r'% error')
        self.transport.set_error_prompt(my_re)
        regex = self.transport.get_error_prompt()
        self.assert_(hasattr(regex, 'groups'))
        self.assert_(regex == my_re)

        self.transport.set_error_prompt()
        regex = self.transport.get_error_prompt()
        self.assert_(hasattr(regex, 'groups'))
        self.assert_(regex == initial_regex)

    def testGetErrorPrompt(self):
        pass # Already tested in testSetErrorPrompt()

    def testSetTimeout(self):
        self.assert_(self.transport.get_timeout() == 30)
        self.transport.set_timeout(60)
        self.assert_(self.transport.get_timeout() == 60)

    def testGetTimeout(self):
        pass # Already tested in testSetTimeout()

    def testConnect(self):
        # Test can not work on the abstract base.
        if self.transport.__class__ == Transport:
            self.assertRaises(Exception, self.transport.connect)
            return
        self.assert_(self.transport.response is None)
        self.transport.connect(self.host)
        self.assert_(self.transport.response is None)
        self.assert_(self.transport.get_host() == self.host)

    def testAuthenticate(self):
        # Test can not work on the abstract base.
        if self.transport.__class__ == Transport:
            self.assertRaises(Exception, self.transport.authenticate, 'test')
            return
        self.doAuthenticate()
        self.assert_(self.transport.response is not None)
        self.assert_(len(self.transport.response) > 0)

    def testIsAuthenticated(self):
        self.failIf(self.transport.is_authenticated())
        # Test can not work on the abstract base.
        if self.transport.__class__ == Transport:
            return
        self.doAuthenticate()
        self.assert_(self.transport.is_authenticated())

    def testAuthorize(self):
        # Test can not work on the abstract base.
        if self.transport.__class__ == Transport:
            self.assertRaises(Exception, self.transport.authorize)
            return
        self.doAuthenticate(wait = False)
        response = self.transport.response
        self.doAuthorize()
        self.failIfEqual(self.transport.response, response)
        self.assert_(len(self.transport.response) > 0)

    def testIsAuthorized(self):
        self.failIf(self.transport.is_authorized())
        # Test can not work on the abstract base.
        if self.transport.__class__ == Transport:
            return
        self.doAuthenticate(wait = False)
        self.failIf(self.transport.is_authorized())
        self.doAuthorize()
        self.assert_(self.transport.is_authorized())

    def testSend(self):
        # Test can not work on the abstract base.
        if self.transport.__class__ == Transport:
            self.assertRaises(Exception, self.transport.send, 'ls')
            return
        self.doAuthenticate()
        self.transport.execute('ls')

        self.transport.send('df\r')
        self.assert_(self.transport.response is not None)
        self.assert_(self.transport.response.startswith('ls'))

        self.transport.send('exit\r')
        self.assert_(self.transport.response is not None)
        self.assert_(self.transport.response.startswith('ls'))

    def testExecute(self):
        # Test can not work on the abstract base.
        if self.transport.__class__ == Transport:
            self.assertRaises(Exception, self.transport.execute, 'ls')
            return
        self.doAuthenticate()
        self.transport.execute('ls')
        self.assert_(self.transport.response is not None)
        self.assert_(self.transport.response.startswith('ls'))

    def testExpect(self):
        # Test can not work on the abstract base.
        if self.transport.__class__ == Transport:
            self.assertRaises(Exception, self.transport.expect, 'ls')
            return
        self.doAuthenticate()
        oldresponse = self.transport.response
        self.transport.send('ls\r')
        self.assertEqual(oldresponse, self.transport.response)
        self.transport.expect(re.compile(r'[\r\n]'))
        self.failIfEqual(oldresponse, self.transport.response)

    def testExpectPrompt(self):
        # Test can not work on the abstract base.
        if self.transport.__class__ == Transport:
            self.assertRaises(Exception, self.transport.expect, 'ls')
            return
        self.doAuthenticate()
        oldresponse = self.transport.response
        self.transport.send('ls\r')
        self.assertEqual(oldresponse, self.transport.response)
        self.transport.expect_prompt()
        self.failIfEqual(oldresponse, self.transport.response)

    def testClose(self):
        # Test can not work on the abstract base.
        if self.transport.__class__ == Transport:
            self.assertRaises(Exception, self.transport.close)
            return
        self.transport.connect(self.host)
        self.transport.close(True)

    def testGetHost(self):
        self.assert_(self.transport.get_host() is None)
        if self.transport.__class__ == Transport:
            return
        self.transport.connect(self.host)
        self.assert_(self.transport.get_host() == self.host)

    def testGuessOs(self):
        self.assertEqual('unknown', self.transport.guess_os())
        # Other tests can not work on the abstract base.
        if self.transport.__class__ == Transport:
            self.assertRaises(Exception, self.transport.close)
            return
        self.transport.connect(self.host)
        self.assertEqual('unknown', self.transport.guess_os())
        self.transport.authenticate(self.user, self.password, wait = True)
        self.assertEqual('shell', self.transport.guess_os())

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(TransportTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
