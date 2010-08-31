import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from ConfigParser                 import RawConfigParser
from Exscript.protocols.Transport import Transport

class TransportTest(unittest.TestCase):
    """
    Since protocols.Transport is abstract, this test is only a base class
    for other protocols. It does not do anything fancy on its own.
    """
    CORRELATE = Transport

    def createTransport(self):
        self.transport = Transport(echo = 0)

    def doAuthenticate(self, wait = True):
        self.transport.connect(self.hostname, self.port)
        self.transport.authenticate(self.user, self.password, wait = wait)

    def doAuthorize(self):
        self.transport.authorize(self.user)

    def setUp(self):
        cfgfile = os.path.join(os.path.dirname(__file__), '..', 'unit_test.cfg')
        cfg     = RawConfigParser()
        cfg.read(cfgfile)
        self.hostname = cfg.get('testhost', 'hostname')
        self.port     = None
        self.user     = cfg.get('testhost', 'user')
        self.password = cfg.get('testhost', 'password')
        self.createTransport()

    def testPrompts(self):
        prompts = ('[sam123@home ~]$',
                   '[MyHost-A1]',
                   '<MyHost-A1>',
                   'sam@knip:~/Code/exscript$',
                   'sam@MyHost-X123>',
                   'sam@MyHost-X123#',
                   'MyHost-ABC-CDE123>',
                   'MyHost-A1#',
                   'S-ABC#',
                   '0123456-1-1-abc#',
                   '0123456-1-1-a>',
                   'MyHost-A1(config)#',
                   'MyHost-A1(config)>',
                   'RP/0/RP0/CPU0:A-BC2#',
                   'FA/0/1/2/3>',
                   'FA/0/1/2/3(config)>',
                   'FA/0/1/2/3(config)#',
                   'ec-c3-c27s99(su)->',
                   'foobar:0>',
                   'admin@s-x-a6.a.bc.de.fg:/# ',
                   'admin@s-x-a6.a.bc.de.fg:/% ')
        notprompts = ('one two',
                      ' [MyHost-A1]',
                      '[edit]\r',
                      '[edit]\n',
                      '[edit foo]\r',
                      '[edit foo]\n',
                      '[edit foo]\r\n',
                      '[edit one two]')
        prompt_re = self.transport.get_prompt()
        for prompt in prompts:
            if not prompt_re.search('\n' + prompt):
                self.fail('Prompt %s does not match exactly.' % prompt)
            if not prompt_re.search('this is a test\r\n' + prompt):
                self.fail('Prompt %s does not match.' % prompt)
            if prompt_re.search('some text ' + prompt):
                self.fail('Prompt %s matches incorrectly.' % repr(prompt))
        for prompt in notprompts:
            if prompt_re.search(prompt):
                self.fail('Prompt %s matches incorrecly.' % repr(prompt))
            if prompt_re.search(prompt + ' '):
                self.fail('Prompt %s matches incorrecly.' % repr(prompt))
            if prompt_re.search('\n' + prompt):
                self.fail('Prompt %s matches incorrecly.' % repr(prompt))

    def testConstructor(self):
        self.assert_(isinstance(self.transport, Transport))

    def testCopy(self):
        self.assert_(self.transport == self.transport.__copy__())

    def testDeepcopy(self):
        self.assert_(self.transport == self.transport.__deepcopy__({}))

    def testIsDummy(self):
        self.assertEqual(self.transport.is_dummy(), False)

    def testSetDriver(self):
        self.assert_(self.transport.get_driver() is not None)
        self.assertEqual(self.transport.get_driver().name, 'generic')

        self.transport.set_driver()
        self.assert_(self.transport.get_driver() is not None)
        self.assertEqual(self.transport.get_driver().name, 'generic')

        self.transport.set_driver('ios')
        self.assert_(self.transport.get_driver() is not None)
        self.assertEqual(self.transport.get_driver().name, 'ios')

        self.transport.set_driver()
        self.assert_(self.transport.get_driver() is not None)
        self.assertEqual(self.transport.get_driver().name, 'generic')

    def testGetDriver(self):
        pass # Already tested in testSetDriver()

    def testSetUsernamePrompt(self):
        initial_regex = self.transport.get_username_prompt()
        self.assert_(hasattr(initial_regex, 'groups'))

        my_re = re.compile(r'% username')
        self.transport.set_username_prompt(my_re)
        regex = self.transport.get_username_prompt()
        self.assert_(hasattr(regex, 'groups'))
        self.assertEqual(regex, my_re)

        self.transport.set_username_prompt()
        regex = self.transport.get_username_prompt()
        self.assert_(hasattr(regex, 'groups'))
        self.assertEqual(regex, initial_regex)

    def testGetUsernamePrompt(self):
        pass # Already tested in testSetUsernamePrompt()

    def testSetPasswordPrompt(self):
        initial_regex = self.transport.get_password_prompt()
        self.assert_(hasattr(initial_regex, 'groups'))

        my_re = re.compile(r'% foobar')
        self.transport.set_password_prompt(my_re)
        regex = self.transport.get_password_prompt()
        self.assert_(hasattr(regex, 'groups'))
        self.assertEqual(regex, my_re)

        self.transport.set_password_prompt()
        regex = self.transport.get_password_prompt()
        self.assert_(hasattr(regex, 'groups'))
        self.assertEqual(regex, initial_regex)

    def testGetPasswordPrompt(self):
        pass # Already tested in testSetPasswordPrompt()

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
        self.assertEqual(regex, my_re)

        self.transport.set_error_prompt()
        regex = self.transport.get_error_prompt()
        self.assert_(hasattr(regex, 'groups'))
        self.assertEqual(regex, initial_regex)

    def testGetErrorPrompt(self):
        pass # Already tested in testSetErrorPrompt()

    def testSetLoginErrorPrompt(self):
        initial_regex = self.transport.get_login_error_prompt()
        self.assert_(hasattr(initial_regex, 'groups'))

        my_re = re.compile(r'% error')
        self.transport.set_login_error_prompt(my_re)
        regex = self.transport.get_login_error_prompt()
        self.assert_(hasattr(regex, 'groups'))
        self.assertEqual(regex, my_re)

        self.transport.set_login_error_prompt()
        regex = self.transport.get_login_error_prompt()
        self.assert_(hasattr(regex, 'groups'))
        self.assertEqual(regex, initial_regex)

    def testGetLoginErrorPrompt(self):
        pass # Already tested in testSetLoginErrorPrompt()

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
        self.assertEqual(self.transport.response, None)
        self.transport.connect(self.hostname, self.port)
        self.assertEqual(self.transport.response, None)
        self.assertEqual(self.transport.get_host(), self.hostname)

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
        self.transport.connect(self.hostname, self.port)
        self.transport.close(True)

    def testGetHost(self):
        self.assert_(self.transport.get_host() is None)
        if self.transport.__class__ == Transport:
            return
        self.transport.connect(self.hostname, self.port)
        self.assertEqual(self.transport.get_host(), self.hostname)

    def testGuessOs(self):
        self.assertEqual('unknown', self.transport.guess_os())
        # Other tests can not work on the abstract base.
        if self.transport.__class__ == Transport:
            self.assertRaises(Exception, self.transport.close)
            return
        self.transport.connect(self.hostname, self.port)
        self.assertEqual('unknown', self.transport.guess_os())
        self.transport.authenticate(self.user, self.password, wait = True)
        self.assertEqual('shell', self.transport.guess_os())

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(TransportTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
