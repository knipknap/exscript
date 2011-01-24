import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from ConfigParser                 import RawConfigParser
from Exscript                     import Account
from Exscript.protocols.Exception import TimeoutException, \
                                         ExpectCancelledException
from Exscript.protocols.Transport import Transport
from Exscript.protocols           import Key

class TransportTest(unittest.TestCase):
    """
    Since protocols.Transport is abstract, this test is only a base class
    for other protocols. It does not do anything fancy on its own.
    """
    CORRELATE = Transport

    def createTransport(self):
        self.transport = Transport(echo = 0)

    def doLogin(self, flush = True):
        self.transport.connect(self.hostname, self.port)
        self.transport.login(self.account, flush = flush)

    def doAuthenticate(self, flush = True):
        self.transport.connect(self.hostname, self.port)
        self.transport.authenticate(self.account, flush = flush)

    def doAppAuthenticate(self, flush = True):
        self.transport.app_authenticate(self.account, flush)

    def doAppAuthorize(self, flush = True):
        self.transport.app_authorize(self.account, flush)

    def setUp(self):
        cfgfile = os.path.join(os.path.dirname(__file__), '..', 'unit_test.cfg')
        cfg     = RawConfigParser()
        cfg.read(cfgfile)
        self.hostname = cfg.get('testhost', 'hostname')
        self.port     = None
        self.user     = cfg.get('testhost', 'user')
        self.password = cfg.get('testhost', 'password')
        self.account  = Account(self.user, password = self.password)
        self.createTransport()

    def _trymatch(self, prompts, string):
        for regex in prompts:
            match = regex.search(string)
            if match:
                return match
        return None

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
            if not self._trymatch(prompt_re, '\n' + prompt):
                self.fail('Prompt %s does not match exactly.' % prompt)
            if not self._trymatch(prompt_re, 'this is a test\r\n' + prompt):
                self.fail('Prompt %s does not match.' % prompt)
            if self._trymatch(prompt_re, 'some text ' + prompt):
                self.fail('Prompt %s matches incorrectly.' % repr(prompt))
        for prompt in notprompts:
            if self._trymatch(prompt_re, prompt):
                self.fail('Prompt %s matches incorrecly.' % repr(prompt))
            if self._trymatch(prompt_re, prompt + ' '):
                self.fail('Prompt %s matches incorrecly.' % repr(prompt))
            if self._trymatch(prompt_re, '\n' + prompt):
                self.fail('Prompt %s matches incorrecly.' % repr(prompt))

    def testConstructor(self):
        self.assert_(isinstance(self.transport, Transport))

    def testCopy(self):
        self.assertEqual(self.transport, self.transport.__copy__())

    def testDeepcopy(self):
        self.assertEqual(self.transport, self.transport.__deepcopy__({}))

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

    def testAutoinit(self):
        self.transport.autoinit()

    def _test_prompt_setter(self, getter, setter):
        initial_regex = getter()
        self.assert_(isinstance(initial_regex, list))
        self.assert_(hasattr(initial_regex[0], 'groups'))

        my_re = re.compile(r'% username')
        setter(my_re)
        regex = getter()
        self.assert_(isinstance(regex, list))
        self.assert_(hasattr(regex[0], 'groups'))
        self.assertEqual(regex[0], my_re)

        setter()
        regex = getter()
        self.assertEqual(regex, initial_regex)

    def testSetUsernamePrompt(self):
        self._test_prompt_setter(self.transport.get_username_prompt,
                                 self.transport.set_username_prompt)

    def testGetUsernamePrompt(self):
        pass # Already tested in testSetUsernamePrompt()

    def testSetPasswordPrompt(self):
        self._test_prompt_setter(self.transport.get_password_prompt,
                                 self.transport.set_password_prompt)

    def testGetPasswordPrompt(self):
        pass # Already tested in testSetPasswordPrompt()

    def testSetPrompt(self):
        self._test_prompt_setter(self.transport.get_prompt,
                                 self.transport.set_prompt)

    def testGetPrompt(self):
        pass # Already tested in testSetPrompt()

    def testSetErrorPrompt(self):
        self._test_prompt_setter(self.transport.get_error_prompt,
                                 self.transport.set_error_prompt)

    def testGetErrorPrompt(self):
        pass # Already tested in testSetErrorPrompt()

    def testSetLoginErrorPrompt(self):
        self._test_prompt_setter(self.transport.get_login_error_prompt,
                                 self.transport.set_login_error_prompt)

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

    def testLogin(self):
        # Test can not work on the abstract base.
        if self.transport.__class__ == Transport:
            self.assertRaises(Exception,
                              self.transport.login,
                              self.account)
            return
        # Password login.
        self.doLogin(flush = False)
        self.assert_(self.transport.response is not None)
        self.assert_(len(self.transport.response) > 0)
        self.assert_(self.transport.is_authenticated())
        self.assert_(self.transport.is_app_authenticated())
        self.assert_(self.transport.is_app_authorized())

        # Key login.
        self.tearDown()
        self.setUp()
        key     = Key.from_file('foo')
        account = Account(self.user, self.password, key = key)
        self.transport.connect(self.hostname, self.port)
        self.transport.login(account, flush = False)
        self.assert_(self.transport.is_authenticated())
        self.assert_(self.transport.is_app_authenticated())
        self.assert_(self.transport.is_app_authorized())

    def testAuthenticate(self):
        # Test can not work on the abstract base.
        if self.transport.__class__ == Transport:
            self.assertRaises(Exception,
                              self.transport.authenticate,
                              self.account)
            return
        # There is no guarantee that the device provided any response
        # during protocol level authentification.
        self.doAuthenticate(flush = False)
        self.assert_(self.transport.is_authenticated())
        self.failIf(self.transport.is_app_authenticated())
        self.failIf(self.transport.is_app_authorized())

    def testIsAuthenticated(self):
        pass # See testAuthenticate()

    def testAppAuthenticate(self):
        # Test can not work on the abstract base.
        if self.transport.__class__ == Transport:
            self.assertRaises(Exception,
                              self.transport.app_authenticate,
                              self.account)
            return
        self.testAuthenticate()
        self.doAppAuthenticate(flush = False)
        self.assert_(self.transport.is_authenticated())
        self.assert_(self.transport.is_app_authenticated())
        self.failIf(self.transport.is_app_authorized())

    def testIsAppAuthenticated(self):
        pass # See testAppAuthenticate()

    def testAppAuthorize(self):
        # Test can not work on the abstract base.
        if self.transport.__class__ == Transport:
            self.assertRaises(Exception, self.transport.app_authorize)
            return
        self.doAuthenticate(flush = False)
        self.doAppAuthenticate(flush = False)
        response = self.transport.response

        # Authorize should see that a prompt is still in the buffer,
        # and do nothing.
        self.doAppAuthorize(flush = False)
        self.assertEqual(self.transport.response, response)
        self.assert_(self.transport.is_authenticated())
        self.assert_(self.transport.is_app_authenticated())
        self.assert_(self.transport.is_app_authorized())

        self.doAppAuthorize(flush = True)
        self.failUnlessEqual(self.transport.response, response)
        self.assert_(self.transport.is_authenticated())
        self.assert_(self.transport.is_app_authenticated())
        self.assert_(self.transport.is_app_authorized())

    def testAutoAppAuthorize(self):
        # Test can not work on the abstract base.
        if self.transport.__class__ == Transport:
            self.assertRaises(TypeError, self.transport.auto_app_authorize)
            return

        self.testAppAuthenticate()
        response = self.transport.response

        # This should do nothing, because our test host does not
        # support AAA. Can't think of a way to test against a
        # device using AAA.
        self.transport.auto_app_authorize(self.account, flush = False)
        self.failUnlessEqual(self.transport.response, response)
        self.assert_(self.transport.is_authenticated())
        self.assert_(self.transport.is_app_authenticated())
        self.assert_(self.transport.is_app_authorized())

        self.transport.auto_app_authorize(self.account, flush = True)
        self.failUnlessEqual(self.transport.response, response)
        self.assert_(self.transport.is_authenticated())
        self.assert_(self.transport.is_app_authenticated())
        self.assert_(self.transport.is_app_authorized())

    def testIsAppAuthorized(self):
        pass # see testAppAuthorize()

    def testSend(self):
        # Test can not work on the abstract base.
        if self.transport.__class__ == Transport:
            self.assertRaises(Exception, self.transport.send, 'ls')
            return
        self.doLogin()
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
        self.doLogin()
        self.transport.execute('ls')
        self.assert_(self.transport.response is not None)
        self.assert_(self.transport.response.startswith('ls'))

    def testWaitfor(self):
        # Test can not work on the abstract base.
        if self.transport.__class__ == Transport:
            self.assertRaises(Exception, self.transport.waitfor, 'ls')
            return
        self.doLogin()
        oldresponse = self.transport.response
        self.transport.send('ls\r')
        self.assertEqual(oldresponse, self.transport.response)
        self.transport.waitfor(re.compile(r'[\r\n]'))
        self.failIfEqual(oldresponse, self.transport.response)
        oldresponse = self.transport.response
        self.transport.waitfor(re.compile(r'[\r\n]'))
        self.assertEqual(oldresponse, self.transport.response)

    def testExpect(self):
        # Test can not work on the abstract base.
        if self.transport.__class__ == Transport:
            self.assertRaises(Exception, self.transport.expect, 'ls')
            return
        self.doLogin()
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
        self.doLogin()
        oldresponse = self.transport.response
        self.transport.send('ls\r')
        self.assertEqual(oldresponse, self.transport.response)
        self.transport.expect_prompt()
        self.failIfEqual(oldresponse, self.transport.response)

    def _cancel_cb(self, data):
        self.transport.cancel_expect()

    def testCancelExpect(self):
        # Test can not work on the abstract base.
        if self.transport.__class__ == Transport:
            self.assertRaises(Exception, self.transport.expect, 'ls')
            return
        self.doLogin()
        oldresponse = self.transport.response
        self.transport.data_received_event.connect(self._cancel_cb)
        self.transport.send('ls\r')
        self.assertEqual(oldresponse, self.transport.response)
        self.assertRaises(ExpectCancelledException,
                          self.transport.expect,
                          'notgoingtohappen')

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
        self.transport.login(self.account)
        self.assert_(self.transport.is_authenticated())
        self.assert_(self.transport.is_app_authenticated())
        self.assert_(self.transport.is_app_authorized())
        self.assertEqual('shell', self.transport.guess_os())

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(TransportTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
