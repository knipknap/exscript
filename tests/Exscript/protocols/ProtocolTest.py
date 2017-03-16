import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

import time
from functools import partial
from ConfigParser                 import RawConfigParser
from Exscript                     import Account, PrivateKey
from Exscript.emulators           import VirtualDevice
from Exscript.protocols.Exception import TimeoutException, \
                                         InvalidCommandException, \
                                         ExpectCancelledException
from Exscript.protocols.Protocol import Protocol

class ProtocolTest(unittest.TestCase):
    """
    Since protocols.Protocol is abstract, this test is only a base class
    for other protocols. It does not do anything fancy on its own.
    """
    CORRELATE = Protocol

    def setUp(self):
        self.hostname = '127.0.0.1'
        self.port     = 1236
        self.user     = 'user'
        self.password = 'password'
        self.account  = Account(self.user, password = self.password)
        self.daemon   = None

        self.createVirtualDevice()
        self.createDaemon()
        if self.daemon is not None:
            self.daemon.start()
            time.sleep(.2)
        self.createProtocol()

    def tearDown(self):
        if self.daemon is not None:
            self.daemon.exit()
            self.daemon.join()

    def createVirtualDevice(self):
        self.banner = 'Welcome to %s!\n' % self.hostname
        self.prompt = self.hostname + '> '
        self.device = VirtualDevice(self.hostname, echo = True)
        ls_response = '-rw-r--r--  1 sab  nmc    1628 Aug 18 10:02 file'
        self.device.add_command('ls',   ls_response)
        self.device.add_command('df',   'foobar')
        self.device.add_command('exit', '')
        self.device.add_command('this-command-causes-an-error',
                                '\ncommand not found')

    def createDaemon(self):
        pass

    def createProtocol(self):
        self.protocol = Protocol()

    def doConnect(self):
        self.protocol.connect(self.hostname, self.port)

    def doLogin(self, flush = True):
        self.doConnect()
        self.protocol.login(self.account, flush = flush)

    def doProtocolAuthenticate(self, flush = True):
        self.doConnect()
        self.protocol.protocol_authenticate(self.account)

    def doAppAuthenticate(self, flush = True):
        self.protocol.app_authenticate(self.account, flush)

    def doAppAuthorize(self, flush = True):
        self.protocol.app_authorize(self.account, flush)

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
        prompt_re = self.protocol.get_prompt()
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
        self.assert_(isinstance(self.protocol, Protocol))

    def testCopy(self):
        self.assertEqual(self.protocol, self.protocol.__copy__())

    def testDeepcopy(self):
        self.assertEqual(self.protocol, self.protocol.__deepcopy__({}))

    def testIsDummy(self):
        self.assertEqual(self.protocol.is_dummy(), False)

    def testSetDriver(self):
        self.assert_(self.protocol.get_driver() is not None)
        self.assertEqual(self.protocol.get_driver().name, 'generic')

        self.protocol.set_driver()
        self.assert_(self.protocol.get_driver() is not None)
        self.assertEqual(self.protocol.get_driver().name, 'generic')

        self.protocol.set_driver('ios')
        self.assert_(self.protocol.get_driver() is not None)
        self.assertEqual(self.protocol.get_driver().name, 'ios')

        self.protocol.set_driver()
        self.assert_(self.protocol.get_driver() is not None)
        self.assertEqual(self.protocol.get_driver().name, 'generic')

    def testGetDriver(self):
        pass # Already tested in testSetDriver()

    def testAutoinit(self):
        self.protocol.autoinit()

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
        self._test_prompt_setter(self.protocol.get_username_prompt,
                                 self.protocol.set_username_prompt)

    def testGetUsernamePrompt(self):
        pass # Already tested in testSetUsernamePrompt()

    def testSetPasswordPrompt(self):
        self._test_prompt_setter(self.protocol.get_password_prompt,
                                 self.protocol.set_password_prompt)

    def testGetPasswordPrompt(self):
        pass # Already tested in testSetPasswordPrompt()

    def testSetPrompt(self):
        self._test_prompt_setter(self.protocol.get_prompt,
                                 self.protocol.set_prompt)

    def testGetPrompt(self):
        pass # Already tested in testSetPrompt()

    def testSetErrorPrompt(self):
        self._test_prompt_setter(self.protocol.get_error_prompt,
                                 self.protocol.set_error_prompt)

    def testGetErrorPrompt(self):
        pass # Already tested in testSetErrorPrompt()

    def testSetLoginErrorPrompt(self):
        self._test_prompt_setter(self.protocol.get_login_error_prompt,
                                 self.protocol.set_login_error_prompt)

    def testGetLoginErrorPrompt(self):
        pass # Already tested in testSetLoginErrorPrompt()

    def testSetConnectTimeout(self):
        self.assert_(self.protocol.get_connect_timeout() == 30)
        self.protocol.set_connect_timeout(60)
        self.assert_(self.protocol.get_connect_timeout() == 60)

    def testGetConnectTimeout(self):
        pass # Already tested in testSetConnectTimeout()

    def testSetTimeout(self):
        self.assert_(self.protocol.get_timeout() == 30)
        self.protocol.set_timeout(60)
        self.assert_(self.protocol.get_timeout() == 60)

    def testGetTimeout(self):
        pass # Already tested in testSetTimeout()

    def testConnect(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            self.assertRaises(Exception, self.protocol.connect)
            return
        self.assertEqual(self.protocol.response, None)
        self.doConnect()
        self.assertEqual(self.protocol.response, None)
        self.assertEqual(self.protocol.get_host(), self.hostname)

    def testLogin(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            self.assertRaises(Exception,
                              self.protocol.login,
                              self.account)
            return
        # Password login.
        self.doLogin(flush = False)
        self.assert_(self.protocol.response is not None)
        self.assert_(len(self.protocol.response) > 0)
        self.assert_(self.protocol.is_protocol_authenticated())
        self.assert_(self.protocol.is_app_authenticated())
        self.assert_(self.protocol.is_app_authorized())

        # Key login.
        self.tearDown()
        self.setUp()
        key     = PrivateKey.from_file('foo', keytype = 'rsa')
        account = Account(self.user, self.password, key = key)
        self.doConnect()
        self.failIf(self.protocol.is_protocol_authenticated())
        self.failIf(self.protocol.is_app_authenticated())
        self.failIf(self.protocol.is_app_authorized())
        self.protocol.login(account, flush = False)
        self.assert_(self.protocol.is_protocol_authenticated())
        self.assert_(self.protocol.is_app_authenticated())
        self.assert_(self.protocol.is_app_authorized())

    def testAuthenticate(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            self.assertRaises(Exception,
                              self.protocol.authenticate,
                              self.account)
            return
        self.doConnect()

        # Password login.
        self.failIf(self.protocol.is_protocol_authenticated())
        self.failIf(self.protocol.is_app_authenticated())
        self.failIf(self.protocol.is_app_authorized())
        self.protocol.authenticate(self.account, flush = False)
        self.assert_(self.protocol.response is not None)
        self.assert_(len(self.protocol.response) > 0)
        self.assert_(self.protocol.is_protocol_authenticated())
        self.assert_(self.protocol.is_app_authenticated())
        self.failIf(self.protocol.is_app_authorized())

        # Key login.
        self.tearDown()
        self.setUp()
        key     = PrivateKey.from_file('foo', keytype = 'rsa')
        account = Account(self.user, self.password, key = key)
        self.doConnect()
        self.failIf(self.protocol.is_protocol_authenticated())
        self.failIf(self.protocol.is_app_authenticated())
        self.failIf(self.protocol.is_app_authorized())
        self.protocol.authenticate(account, flush = False)
        self.assert_(self.protocol.is_protocol_authenticated())
        self.assert_(self.protocol.is_app_authenticated())
        self.failIf(self.protocol.is_app_authorized())

    def testProtocolAuthenticate(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            self.protocol.protocol_authenticate(self.account)
            return
        # There is no guarantee that the device provided any response
        # during protocol level authentification.
        self.doProtocolAuthenticate(flush = False)
        self.assert_(self.protocol.is_protocol_authenticated())
        self.failIf(self.protocol.is_app_authenticated())
        self.failIf(self.protocol.is_app_authorized())

    def testIsProtocolAuthenticated(self):
        pass # See testProtocolAuthenticate()

    def testAppAuthenticate(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            self.assertRaises(Exception,
                              self.protocol.app_authenticate,
                              self.account)
            return
        self.testProtocolAuthenticate()
        self.doAppAuthenticate(flush = False)
        self.assert_(self.protocol.is_protocol_authenticated())
        self.assert_(self.protocol.is_app_authenticated())
        self.failIf(self.protocol.is_app_authorized())

    def testIsAppAuthenticated(self):
        pass # See testAppAuthenticate()

    def testAppAuthorize(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            self.assertRaises(Exception, self.protocol.app_authorize)
            return
        self.doProtocolAuthenticate(flush = False)
        self.doAppAuthenticate(flush = False)
        response = self.protocol.response

        # Authorize should see that a prompt is still in the buffer,
        # and do nothing.
        self.doAppAuthorize(flush = False)
        self.assertEqual(self.protocol.response, response)
        self.assert_(self.protocol.is_protocol_authenticated())
        self.assert_(self.protocol.is_app_authenticated())
        self.assert_(self.protocol.is_app_authorized())

        self.doAppAuthorize(flush = True)
        self.failUnlessEqual(self.protocol.response, response)
        self.assert_(self.protocol.is_protocol_authenticated())
        self.assert_(self.protocol.is_app_authenticated())
        self.assert_(self.protocol.is_app_authorized())

    def testAppAuthorize2(self):
        # Same test as above, but using flush=True all the way.
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            self.assertRaises(Exception, self.protocol.app_authorize)
            return
        self.doProtocolAuthenticate(flush=True)
        self.doAppAuthenticate(flush=True)
        response = self.protocol.response

        # Authorize should see that a prompt is still in the buffer,
        # and do nothing.
        self.doAppAuthorize(flush=True)
        self.assert_(self.protocol.is_protocol_authenticated())
        self.assert_(self.protocol.is_app_authenticated())
        self.assert_(self.protocol.is_app_authorized())

    def testAutoAppAuthorize(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            self.assertRaises(TypeError, self.protocol.auto_app_authorize)
            return

        self.testAppAuthenticate()
        response = self.protocol.response

        # This should do nothing, because our test host does not
        # support AAA. Can't think of a way to test against a
        # device using AAA.
        self.protocol.auto_app_authorize(self.account, flush = False)
        self.failUnlessEqual(self.protocol.response, response)
        self.assert_(self.protocol.is_protocol_authenticated())
        self.assert_(self.protocol.is_app_authenticated())
        self.assert_(self.protocol.is_app_authorized())

        self.protocol.auto_app_authorize(self.account, flush = True)
        self.failUnlessEqual(self.protocol.response, response)
        self.assert_(self.protocol.is_protocol_authenticated())
        self.assert_(self.protocol.is_app_authenticated())
        self.assert_(self.protocol.is_app_authorized())

    def testIsAppAuthorized(self):
        pass # see testAppAuthorize()

    def testSend(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            self.assertRaises(Exception, self.protocol.send, 'ls')
            return
        self.doLogin()
        self.protocol.execute('ls')

        self.protocol.send('df\r')
        self.assert_(self.protocol.response is not None)
        self.assert_(self.protocol.response.startswith('ls'))

        self.protocol.send('exit\r')
        self.assert_(self.protocol.response is not None)
        self.assert_(self.protocol.response.startswith('ls'))

    def testExecute(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            self.assertRaises(Exception, self.protocol.execute, 'ls')
            return
        self.doLogin()
        self.protocol.execute('ls')
        self.assert_(self.protocol.response is not None)
        self.assert_(self.protocol.response.startswith('ls'))

        # Make sure that we raise an error if the device responds
        # with something that matches any of the error prompts.
        self.protocol.set_error_prompt('.')
        self.assertRaises(InvalidCommandException,
                          self.protocol.execute,
                          'this-command-causes-an-error')

    def testWaitfor(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            self.assertRaises(Exception, self.protocol.waitfor, 'ls')
            return
        self.doLogin()
        oldresponse = self.protocol.response
        self.protocol.send('ls\r')
        self.assertEqual(oldresponse, self.protocol.response)
        self.protocol.waitfor(re.compile(r'[\r\n]'))
        self.failIfEqual(oldresponse, self.protocol.response)
        oldresponse = self.protocol.response
        self.protocol.waitfor(re.compile(r'[\r\n]'))
        self.assertEqual(oldresponse, self.protocol.response)

    def testExpect(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            self.assertRaises(Exception, self.protocol.expect, 'ls')
            return
        self.doLogin()
        oldresponse = self.protocol.response
        self.protocol.send('ls\r')
        self.assertEqual(oldresponse, self.protocol.response)
        self.protocol.expect(re.compile(r'[\r\n]'))
        self.failIfEqual(oldresponse, self.protocol.response)

    def testExpectPrompt(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            self.assertRaises(Exception, self.protocol.expect, 'ls')
            return
        self.doLogin()
        oldresponse = self.protocol.response
        self.protocol.send('ls\r')
        self.assertEqual(oldresponse, self.protocol.response)
        self.protocol.expect_prompt()
        self.failIfEqual(oldresponse, self.protocol.response)

    def testAddMonitor(self):
        # Set the monitor callback up.
        def monitor_cb(thedata, *args, **kwargs):
            thedata['args']   = args
            thedata['kwargs'] = kwargs
        data = {}
        self.protocol.add_monitor('abc', partial(monitor_cb, data))

        # Simulate some non-matching data.
        self.protocol.buffer.append('aaa')
        self.assertEqual(data, {})

        # Simulate some matching data.
        self.protocol.buffer.append('abc')
        self.assertEqual(len(data.get('args')), 3)
        self.assertEqual(data.get('args')[0], self.protocol)
        self.assertEqual(data.get('args')[1], 0)
        self.assertEqual(data.get('args')[2].group(0), 'abc')
        self.assertEqual(data.get('kwargs'), {})

    def testGetBuffer(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            return
        self.assertEqual(str(self.protocol.buffer), '')
        self.doLogin()
        # Depending on whether the connected host sends a banner,
        # the buffer may or may not contain anything now.

        before = str(self.protocol.buffer)
        self.protocol.send('ls\r')
        self.protocol.waitfor(self.protocol.get_prompt())
        self.assertNotEqual(str(self.protocol.buffer), before)

    def _cancel_cb(self, data):
        self.protocol.cancel_expect()

    def testCancelExpect(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            return
        self.doLogin()
        oldresponse = self.protocol.response
        self.protocol.data_received_event.connect(self._cancel_cb)
        self.protocol.send('ls\r')
        self.assertEqual(oldresponse, self.protocol.response)
        self.assertRaises(ExpectCancelledException,
                          self.protocol.expect,
                          'notgoingtohappen')

    def testInteract(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            self.assertRaises(Exception, self.protocol.interact)
            return
        # Can't really be tested.

    def testClose(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            self.assertRaises(Exception, self.protocol.close)
            return
        self.doConnect()
        self.protocol.close(True)

    def testGetHost(self):
        self.assert_(self.protocol.get_host() is None)
        if self.protocol.__class__ == Protocol:
            return
        self.doConnect()
        self.assertEqual(self.protocol.get_host(), self.hostname)

    def testGuessOs(self):
        self.assertEqual('unknown', self.protocol.guess_os())
        # Other tests can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            self.assertRaises(Exception, self.protocol.close)
            return
        self.doConnect()
        self.assertEqual('unknown', self.protocol.guess_os())
        self.protocol.login(self.account)
        self.assert_(self.protocol.is_protocol_authenticated())
        self.assert_(self.protocol.is_app_authenticated())
        self.assert_(self.protocol.is_app_authorized())
        self.assertEqual('shell', self.protocol.guess_os())

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(ProtocolTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
