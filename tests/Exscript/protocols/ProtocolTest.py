import os
import re
import tempfile
import unittest
import unittest.mock


import time
from functools import partial

from Exscript import Account, PrivateKey
from Exscript.emulators import VirtualDevice
from Exscript.protocols import drivers
from Exscript.protocols.exception import (
    ExpectCancelledException,
    InvalidCommandException,
    ProtocolException,
    TimeoutException,
)
from Exscript.protocols.protocol import Protocol


class ProtocolTest(unittest.TestCase):

    """
    Since protocols.Protocol is abstract, this test is only a base class
    for other protocols. It does not do anything fancy on its own.
    """
    CORRELATE = Protocol

    def setUp(self):
        self.hostname = '127.0.0.1'
        self.port = 1236
        self.user = 'user'
        self.password = 'password'
        self.account = Account(self.user, password=self.password)
        self.daemon = None

        self.createVirtualDevice()
        self.createDaemon()
        if self.daemon is not None:
            self.daemon.start()
            time.sleep(.2)
            # LIFO cleanup order!
            self.addCleanup(self.daemon.join)
            self.addCleanup(self.daemon.exit)
        self.createProtocol()

    def tearDown(self):
        self.protocol.close(force=True)
        if self.daemon is not None:
            self.daemon.exit()
            self.daemon.join()

    def createVirtualDevice(self):
        self.banner = 'Welcome to %s!\n' % self.hostname
        self.prompt = self.hostname + '> '
        self.device = VirtualDevice(self.hostname, echo=True)
        ls_response = '-rw-r--r--  1 sab  nmc    1628 Aug 18 10:02 file'
        self.device.add_command('ls',   ls_response)
        self.device.add_command('df',   'foobar')
        self.device.add_command('exit', '')
        self.device.add_command('this-command-causes-an-error',
                                '\ncommand not found')

    def createDaemon(self):
        pass

    def createProtocol(self):
        self.protocol = Protocol(timeout=1, debug=5)

    def disableDriver(self):
        self.assertIn(drivers.driver_map, 'ios')
        drivers.disable_driver('ios')
        self.assertNotIn(drivers.driver_map, 'ios')

    def doConnect(self):
        self.protocol.connect(self.hostname, self.port)

    def doLogin(self, flush=True):
        self.doConnect()
        self.protocol.login(self.account, flush=flush)

    def doProtocolAuthenticate(self, flush=True):
        self.doConnect()
        self.protocol.protocol_authenticate(self.account)

    def doAppAuthenticate(self, flush=True):
        self.protocol.app_authenticate(self.account, flush)

    def doAppAuthorize(self, flush=True):
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
        self.assertIsInstance(self.protocol, Protocol)

    def testMandatorySubclassAttributes(self):
        self.assertTrue(self.protocol._name is not None)
        self.assertTrue(self.protocol._name.isalpha())
        self.assertTrue(self.protocol._name.islower())
        if self.protocol.__class__ != Protocol:
            self.assertTrue(self.protocol._default_port is not None)
            self.assertTrue(0 <= self.protocol._default_port <= 65535)

    def testCopy(self):
        self.assertEqual(self.protocol, self.protocol.__copy__())

    def testDeepcopy(self):
        self.assertEqual(self.protocol, self.protocol.__deepcopy__({}))

    def testIsDummy(self):
        self.assertEqual(self.protocol.is_dummy(), False)

    def testSetDriver(self):
        self.assertTrue(self.protocol.get_driver() is not None)
        self.assertEqual(self.protocol.get_driver().name, 'generic')

        self.protocol.set_driver()
        self.assertTrue(self.protocol.get_driver() is not None)
        self.assertEqual(self.protocol.get_driver().name, 'generic')

        self.protocol.set_driver('ios')
        self.assertTrue(self.protocol.get_driver() is not None)
        self.assertEqual(self.protocol.get_driver().name, 'ios')

        self.protocol.set_driver()
        self.assertTrue(self.protocol.get_driver() is not None)
        self.assertEqual(self.protocol.get_driver().name, 'generic')

    def testGetDriver(self):
        pass  # Already tested in testSetDriver()

    def testGetBanner(self):
        self.assertEqual(self.protocol.get_banner(), None)
        if self.protocol.__class__ == Protocol:
            self.assertRaises(Exception, self.protocol.connect)
            return
        self.doConnect()
        self.assertEqual(self.protocol.get_banner(), None)

    def testGetRemoteVersion(self):
        self.assertEqual(self.protocol.get_remote_version(), None)
        if self.protocol.__class__ == Protocol:
            self.assertRaises(Exception, self.protocol.connect)
            return
        self.doConnect()
        self.assertEqual(self.protocol.get_remote_version(), None)

    def testAutoinit(self):
        self.protocol.autoinit()

    def _test_prompt_setter(self, getter, setter):
        initial_regex = getter()
        self.assertIsInstance(initial_regex, list)
        self.assertTrue(hasattr(initial_regex[0], 'groups'))

        my_re = re.compile(r'% username')

        # Extends an implicit copy of the initial pattern list.
        try:
            setter(my_re, extend=True)  # not all setters have "extend" parameter
        except TypeError:
            pass
        else:
            regex = getter()
            self.assertIsInstance(regex, list)
            self.assertEqual(regex, initial_regex + [my_re])

        setter(my_re)
        regex = getter()
        self.assertIsInstance(regex, list)
        self.assertTrue(hasattr(regex[0], 'groups'))
        self.assertEqual(regex[0], my_re)

        # Extends the manually set pattern list.
        try:
            setter(my_re, extend=True)  # not all setters have "extend" parameter
        except TypeError:
            pass
        else:
            regex = getter()
            self.assertIsInstance(regex, list)
            self.assertEqual(regex, [my_re, my_re])

        setter()
        regex = getter()
        self.assertEqual(regex, initial_regex)

    def testSetUsernamePrompt(self):
        self._test_prompt_setter(self.protocol.get_username_prompt,
                                 self.protocol.set_username_prompt)

    def testGetUsernamePrompt(self):
        pass  # Already tested in testSetUsernamePrompt()

    def testSetPasswordPrompt(self):
        self._test_prompt_setter(self.protocol.get_password_prompt,
                                 self.protocol.set_password_prompt)

    def testGetPasswordPrompt(self):
        pass  # Already tested in testSetPasswordPrompt()

    def testSetPrompt(self):
        self._test_prompt_setter(self.protocol.get_prompt,
                                 self.protocol.set_prompt)

    def testGetPrompt(self):
        pass  # Already tested in testSetPrompt()

    def testSetErrorPrompt(self):
        self._test_prompt_setter(self.protocol.get_error_prompt,
                                 self.protocol.set_error_prompt)

    def testGetErrorPrompt(self):
        pass  # Already tested in testSetErrorPrompt()

    def testSetLoginErrorPrompt(self):
        self._test_prompt_setter(self.protocol.get_login_error_prompt,
                                 self.protocol.set_login_error_prompt)

    def testGetLoginErrorPrompt(self):
        pass  # Already tested in testSetLoginErrorPrompt()

    def testSetConnectTimeout(self):
        self.assertEqual(self.protocol.get_connect_timeout(), 30)
        self.protocol.set_connect_timeout(60)
        self.assertEqual(self.protocol.get_connect_timeout(), 60)

    def testGetConnectTimeout(self):
        pass  # Already tested in testSetConnectTimeout()

    def testSetTimeout(self):
        self.assertEqual(self.protocol.get_timeout(), 1)
        self.protocol.set_timeout(60)
        self.assertEqual(self.protocol.get_timeout(), 60)

    def testGetTimeout(self):
        pass  # Already tested in testSetTimeout()

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
        self.doLogin(flush=False)
        self.assertTrue(self.protocol.response is not None)
        self.assertTrue(len(self.protocol.response) > 0)
        self.assertTrue(self.protocol.is_protocol_authenticated())
        self.assertTrue(self.protocol.is_app_authenticated())
        self.assertTrue(self.protocol.is_app_authorized())

        # Key login.
        self.tearDown()
        self.setUp()
        key = PrivateKey.from_file('foo', keytype='rsa')
        account = Account(self.user, self.password, key=key)
        self.doConnect()
        self.assertFalse(self.protocol.is_protocol_authenticated())
        self.assertFalse(self.protocol.is_app_authenticated())
        self.assertFalse(self.protocol.is_app_authorized())
        self.protocol.login(account, flush=False)
        self.assertTrue(self.protocol.is_protocol_authenticated())
        self.assertTrue(self.protocol.is_app_authenticated())
        self.assertTrue(self.protocol.is_app_authorized())

    def testAuthenticate(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            self.assertRaises(Exception,
                              self.protocol.authenticate,
                              self.account)
            return
        self.doConnect()

        # Password login.
        self.assertFalse(self.protocol.is_protocol_authenticated())
        self.assertFalse(self.protocol.is_app_authenticated())
        self.assertFalse(self.protocol.is_app_authorized())
        self.protocol.authenticate(self.account, flush=False)
        self.assertTrue(self.protocol.response is not None)
        self.assertTrue(len(self.protocol.response) > 0)
        self.assertTrue(self.protocol.is_protocol_authenticated())
        self.assertTrue(self.protocol.is_app_authenticated())
        self.assertFalse(self.protocol.is_app_authorized())

        # Key login.
        self.tearDown()
        self.setUp()
        key = PrivateKey.from_file('foo', keytype='rsa')
        account = Account(self.user, self.password, key=key)
        self.doConnect()
        self.assertFalse(self.protocol.is_protocol_authenticated())
        self.assertFalse(self.protocol.is_app_authenticated())
        self.assertFalse(self.protocol.is_app_authorized())
        self.protocol.authenticate(account, flush=False)
        self.assertTrue(self.protocol.is_protocol_authenticated())
        self.assertTrue(self.protocol.is_app_authenticated())
        self.assertFalse(self.protocol.is_app_authorized())

    def testProtocolAuthenticate(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            self.protocol.protocol_authenticate(self.account)
            return
        # There is no guarantee that the device provided any response
        # during protocol level authentification.
        self.doProtocolAuthenticate(flush=False)
        self.assertTrue(self.protocol.is_protocol_authenticated())
        self.assertFalse(self.protocol.is_app_authenticated())
        self.assertFalse(self.protocol.is_app_authorized())

    def testIsProtocolAuthenticated(self):
        pass  # See testProtocolAuthenticate()

    def testAppAuthenticate(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            self.assertRaises(Exception,
                              self.protocol.app_authenticate,
                              self.account)
            return
        self.testProtocolAuthenticate()
        self.doAppAuthenticate(flush=False)
        self.assertTrue(self.protocol.is_protocol_authenticated())
        self.assertTrue(self.protocol.is_app_authenticated())
        self.assertFalse(self.protocol.is_app_authorized())

    def testIsAppAuthenticated(self):
        pass  # See testAppAuthenticate()

    def testAppAuthorize(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            self.assertRaises(Exception, self.protocol.app_authorize)
            return
        self.doProtocolAuthenticate(flush=False)
        self.doAppAuthenticate(flush=False)
        response = self.protocol.response

        # Authorize should see that a prompt is still in the buffer,
        # and do nothing.
        self.doAppAuthorize(flush=False)
        self.assertEqual(self.protocol.response, response)
        self.assertTrue(self.protocol.is_protocol_authenticated())
        self.assertTrue(self.protocol.is_app_authenticated())
        self.assertTrue(self.protocol.is_app_authorized())

        self.doAppAuthorize(flush=True)
        self.assertEqual(self.protocol.response, response)
        self.assertTrue(self.protocol.is_protocol_authenticated())
        self.assertTrue(self.protocol.is_app_authenticated())
        self.assertTrue(self.protocol.is_app_authorized())

    def testAppAuthorize2(self):
        # Same test as above, but using flush=True all the way.
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            self.assertRaises(Exception, self.protocol.app_authorize)
            return
        self.doProtocolAuthenticate(flush=True)
        self.doAppAuthenticate(flush=True)

        # At this point app_authorize should fail because the buffer is
        # empty due to flush=True above. In other words, app_authorize
        # will wait for a prompt until a timeout happens.
        self.assertRaises(TimeoutException, self.doAppAuthorize)
        self.assertTrue(self.protocol.is_protocol_authenticated())
        self.assertTrue(self.protocol.is_app_authenticated())
        self.assertFalse(self.protocol.is_app_authorized())

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
        self.protocol.auto_app_authorize(self.account, flush=False)
        self.assertEqual(self.protocol.response, response)
        self.assertTrue(self.protocol.is_protocol_authenticated())
        self.assertTrue(self.protocol.is_app_authenticated())
        self.assertTrue(self.protocol.is_app_authorized())

        self.protocol.auto_app_authorize(self.account, flush=True)
        self.assertEqual(self.protocol.response, response)
        self.assertTrue(self.protocol.is_protocol_authenticated())
        self.assertTrue(self.protocol.is_app_authenticated())
        self.assertTrue(self.protocol.is_app_authorized())

    def testIsAppAuthorized(self):
        pass  # see testAppAuthorize()

    def testGetHost(self):
        self.assertTrue(self.protocol.get_host() is None)
        if self.protocol.__class__ == Protocol:
            return
        self.doConnect()
        self.assertEqual(self.protocol.get_host(), self.hostname)

    def testGetProtocol(self):
        expected = type(self.protocol).__name__.lower().strip('0123456789')
        self.assertTrue(self.protocol.get_protocol() == expected)

    def testGetResponse(self):
        # No response yet — should return empty string.
        self.protocol.response = None
        self.assertEqual('', self.protocol.get_response())
        self.protocol.response = ''
        self.assertEqual('', self.protocol.get_response())

        # strip_command: first line (command echo) is removed.
        self.protocol.response = 'show version\nCisco IOS 15.1\n'
        self.assertEqual('Cisco IOS 15.1\n', self.protocol.get_response())
        # strip_command: command echo only, no output — returns empty string.
        self.protocol.response = 'show version'
        self.assertEqual('', self.protocol.get_response())
        # strip_command=False: first line is kept.
        self.protocol.response = 'show version\nCisco IOS 15.1\n'
        self.assertEqual(
            'show version\nCisco IOS 15.1\n',
            self.protocol.get_response(strip_command=False),
        )

        # strip_chars: CR, NUL, BEL, BS are removed.
        self.protocol.response = 'cmd\r\nline one\x00\x07\x08\r\nline two\r\n'
        self.assertEqual('line one\nline two\n', self.protocol.get_response())
        # strip_chars='': disables all char stripping.
        self.assertEqual(
            'line one\x00\x07\x08\nline two\n',
            self.protocol.get_response(strip_chars=''),
        )

        # strip_ansi: CSI color/cursor sequences are removed.
        self.protocol.response = 'cmd\n\x1b[1;32mgreen text\x1b[0m\n'
        self.assertEqual('green text\n', self.protocol.get_response())
        # strip_ansi: full CSI with intermediate bytes is handled.
        self.protocol.response = 'cmd\n\x1b[ Msome text\n'
        self.assertEqual('some text\n', self.protocol.get_response())
        # strip_ansi: lone ESC is removed.
        self.protocol.response = 'cmd\nstray\x1btext\n'
        self.assertEqual('straytext\n', self.protocol.get_response())
        # strip_ansi=False: ANSI sequences are preserved.
        self.protocol.response = 'cmd\n\x1b[32mtext\x1b[0m\n'
        self.assertEqual(
            '\x1b[32mtext\x1b[0m\n',
            self.protocol.get_response(strip_ansi=False),
        )

        # Combined: real-world router output with CR, ANSI, and command echo.
        self.protocol.response = (
            'show ip int brief\r\n'
            '\x1b[1mInterface\x1b[0m\tIP-Address\r\n'
            'GigabitEthernet0    10.0.0.1\r\n'
        )
        self.assertEqual(
            'Interface\tIP-Address\nGigabitEthernet0    10.0.0.1\n',
            self.protocol.get_response(),
        )

    def testCleanupResponse(self):
        # Tested indirectly through testGetResponse().
        pass

    def testGuessOs(self):
        self.assertEqual('unknown', self.protocol.guess_os())
        # Other tests can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            return
        self.doConnect()
        self.assertEqual('unknown', self.protocol.guess_os())
        self.protocol.login(self.account)
        self.assertTrue(self.protocol.is_protocol_authenticated())
        self.assertTrue(self.protocol.is_app_authenticated())
        self.assertTrue(self.protocol.is_app_authorized())
        self.assertEqual('shell', self.protocol.guess_os())

    def testSend(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            self.assertRaises(Exception, self.protocol.send, 'ls')
            return
        self.doLogin()
        self.protocol.execute('ls')
        self.assertTrue(self.protocol.response is not None)
        self.assertTrue(self.protocol.response.startswith('ls'))

        self.protocol.send('df\r')
        self.assertTrue(self.protocol.response is None)

        self.protocol.send('exit\r')
        self.assertTrue(self.protocol.response is None)

    def testExecute(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            self.assertRaises(Exception, self.protocol.execute, 'ls')
            return
        self.doLogin()
        self.protocol.execute('ls')
        self.assertTrue(self.protocol.response is not None)
        self.assertTrue(self.protocol.response.startswith('ls'))

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
        self.protocol.send('ls\r')
        self.protocol.waitfor(re.compile(r'[\r\n]'))
        self.assertTrue(self.protocol.response is not None)
        self.assertTrue(self.protocol.response.startswith('ls'))
        self.protocol.waitfor(re.compile(r'[\r\n]'))
        self.assertTrue(self.protocol.response is not None)
        self.assertTrue(self.protocol.response.startswith('ls'))

    def testExpect(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            self.assertRaises(Exception, self.protocol.expect, 'ls')
            return
        self.doLogin()
        self.protocol.send('ls\r')
        self.protocol.expect(re.compile(r'[\r\n]'))
        self.assertTrue(self.protocol.response is not None)
        self.assertTrue(self.protocol.response.startswith('ls'))

    def testExpectPrompt(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            self.assertRaises(Exception, self.protocol.expect, 'ls')
            return
        self.doLogin()
        self.protocol.send('ls\r')
        self.protocol.expect_prompt()
        self.assertTrue(self.protocol.response is not None)
        self.assertTrue(self.protocol.response.startswith('ls'))

    def testAddMonitor(self):
        # Set the monitor callback up.
        def monitor_cb(thedata, *args, **kwargs):
            thedata['args'] = args
            thedata['kwargs'] = kwargs
        data = {}
        self.protocol.add_monitor('abc', partial(monitor_cb, data))

        # Simulate some non-matching data.
        self.protocol._buffer.append(u'aaa')
        self.assertEqual(data, {})

        # Simulate some matching data.
        self.protocol._buffer.append(u'abc')
        self.assertEqual(len(data.get('args')), 3)
        self.assertEqual(data.get('args')[0], self.protocol)
        self.assertEqual(data.get('args')[1], 0)
        self.assertEqual(data.get('args')[2].group(0), 'abc')
        self.assertEqual(data.get('kwargs'), {})

    def testGetBuffer(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            return
        self.assertEqual(str(self.protocol._buffer), '')
        self.doLogin()
        # Depending on whether the connected host sends a banner,
        # the buffer may or may not contain anything now.

        before = str(self.protocol._buffer)
        self.protocol.send('ls\r')
        self.protocol.waitfor(self.protocol.get_prompt())
        self.assertNotEqual(str(self.protocol._buffer), before)

    def _cancel_cb(self, data):
        self.protocol.cancel_expect()

    def testCancelExpect(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            return
        self.doLogin()
        self.protocol.data_received_event.connect(self._cancel_cb)
        self.protocol.send('ls\r')
        self.assertRaises(ExpectCancelledException,
                          self.protocol.expect,
                          'notgoingtohappen')

    def testInteract(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            self.assertRaises(Exception, self.protocol.interact)
            return
        # Can't really be tested.

    def testSwitchDeviceContext(self):
        # Stack is empty at construction time.
        self.assertEqual(self.protocol._device_context_stack, [])

        # Set up initial device state including OS guesser to verify capture/restore.
        # Simulate guesser state that would have been built up during a session.
        self.protocol._os_guesser._info            = {'os': ('ios', 80)}
        self.protocol._os_guesser._auth_buffer     = 'banner data'
        self.protocol._os_guesser._protocol_buffer = 'SSH-2.0-OpenSSH'
        self.protocol._os_guesser._response_buffer = 'router#'
        self.protocol._auto_driver = drivers.driver_map[self.protocol.guess_os()]
        self.protocol._app_authenticated     = True
        self.protocol._app_authorized        = True
        self.protocol._last_account          = self.account
        self.protocol._manual_prompt_re      = [re.compile(r'router#')]
        self.protocol._manual_error_re       = [re.compile(r'% Error')]
        self.protocol._manual_user_re        = [re.compile(r'Username:')]
        self.protocol._manual_password_re    = [re.compile(r'Password:')]
        self.protocol._manual_login_error_re = [re.compile(r'Login failed')]
        self.protocol.set_driver('junos')

        # -- Switch to a remote hop (default: reset_auth=True) --
        self.protocol.switch_device_context()
        self.assertEqual(len(self.protocol._device_context_stack), 1)
        snapshot = self.protocol._device_context_stack[0]

        # Original state captured correctly — auth.
        self.assertEqual(snapshot['app_authenticated'], True)
        self.assertEqual(snapshot['app_authorized'], True)
        self.assertIs(snapshot['last_account'], self.account)
        # Original state captured correctly — guesser.
        self.assertEqual(snapshot['guesser_info'], {'os': ('ios', 80)})
        self.assertEqual(snapshot['guesser_auth_buffer'], 'banner data')
        self.assertEqual(snapshot['guesser_protocol_buffer'], 'SSH-2.0-OpenSSH')
        self.assertEqual(snapshot['guesser_response_buffer'], 'router#')
        # Original state captured correctly — driver.
        self.assertIsNotNone(snapshot['auto_driver'])
        self.assertEqual(snapshot['auto_driver'].name, 'ios')
        self.assertIsNotNone(snapshot['manual_driver'])
        self.assertEqual(snapshot['manual_driver'].name, 'junos')
        # Original state captured correctly — patterns.
        self.assertIsNotNone(snapshot['manual_prompt_re'])
        self.assertIsNotNone(snapshot['manual_error_re'])
        self.assertIsNotNone(snapshot['manual_user_re'])
        self.assertIsNotNone(snapshot['manual_password_re'])
        self.assertIsNotNone(snapshot['manual_login_error_re'])

        # New context: auth reset.
        self.assertFalse(self.protocol.is_app_authenticated())
        self.assertFalse(self.protocol.is_app_authorized())
        self.assertIsNone(self.protocol._last_account)
        # New context: guesser reset — info back to unknown, all buffers empty.
        self.assertEqual(self.protocol._os_guesser._info, {'os': ('unknown', 0)})
        self.assertEqual(self.protocol._os_guesser._auth_buffer, '')
        self.assertEqual(self.protocol._os_guesser._protocol_buffer, '')
        self.assertEqual(self.protocol._os_guesser._response_buffer, '')
        # New context: manual driver and all patterns cleared.
        self.assertIsNone(self.protocol._manual_driver)
        self.assertIsNone(self.protocol._manual_prompt_re)
        self.assertIsNone(self.protocol._manual_error_re)
        self.assertIsNone(self.protocol._manual_user_re)
        self.assertIsNone(self.protocol._manual_password_re)
        self.assertIsNone(self.protocol._manual_login_error_re)
        # New context: auto driver follows guesser (unknown → generic).
        self.assertEqual(self.protocol.get_driver().name, 'generic')

        # -- Nested switch: local shell (reset_auth=False, no driver param) --
        hop_account = Account('hop_user', password='hop_pass')
        self.protocol._app_authenticated = True   # simulate auth on the hop
        self.protocol._app_authorized    = True
        self.protocol._last_account      = hop_account
        self.protocol.switch_device_context(reset_auth=False)
        self.assertEqual(len(self.protocol._device_context_stack), 2)

        # Auth flags are preserved when reset_auth=False.
        self.assertTrue(self.protocol.is_app_authenticated())
        self.assertTrue(self.protocol.is_app_authorized())
        # last_account is preserved when reset_auth=False (same device, same account).
        self.assertIs(self.protocol._last_account, hop_account)
        # Manual driver auto-cleared on switch; caller sets it explicitly if needed.
        self.assertIsNone(self.protocol._manual_driver)
        self.protocol.set_driver('shell')
        self.assertEqual(self.protocol.get_driver().name, 'shell')

        # -- Restore to the first hop context --
        self.protocol.restore_device_context()
        self.assertEqual(len(self.protocol._device_context_stack), 1)

        # Auth was True in the first-hop context when the nested switch was called
        # (we simulated a successful login on the hop before entering the local shell).
        self.assertTrue(self.protocol.is_app_authenticated())
        self.assertTrue(self.protocol.is_app_authorized())
        self.assertIs(self.protocol._last_account, hop_account)
        # First-hop context had a reset guesser.
        self.assertEqual(self.protocol._os_guesser._info, {'os': ('unknown', 0)})
        self.assertEqual(self.protocol._os_guesser._auth_buffer, '')
        self.assertEqual(self.protocol._os_guesser._protocol_buffer, '')
        self.assertEqual(self.protocol._os_guesser._response_buffer, '')
        # First-hop context had auto driver (generic) and no manual driver/patterns.
        self.assertIsNone(self.protocol._manual_driver)
        self.assertIsNone(self.protocol._manual_prompt_re)
        self.assertIsNone(self.protocol._manual_error_re)
        self.assertIsNone(self.protocol._manual_user_re)
        self.assertIsNone(self.protocol._manual_password_re)
        self.assertIsNone(self.protocol._manual_login_error_re)

        # -- Restore to the original context --
        self.protocol.restore_device_context()
        self.assertEqual(self.protocol._device_context_stack, [])

        # Auth restored.
        self.assertTrue(self.protocol.is_app_authenticated())
        self.assertTrue(self.protocol.is_app_authorized())
        self.assertIs(self.protocol._last_account, self.account)
        # Guesser restored.
        self.assertEqual(self.protocol._os_guesser._info, {'os': ('ios', 80)})
        self.assertEqual(self.protocol._os_guesser._auth_buffer, 'banner data')
        self.assertEqual(self.protocol._os_guesser._protocol_buffer, 'SSH-2.0-OpenSSH')
        self.assertEqual(self.protocol._os_guesser._response_buffer, 'router#')
        # Driver restored (manual junos takes effect).
        self.assertEqual(self.protocol.get_driver().name, 'junos')
        # Patterns restored.
        self.assertIsNotNone(self.protocol._manual_prompt_re)
        self.assertIsNotNone(self.protocol._manual_error_re)
        self.assertIsNotNone(self.protocol._manual_user_re)
        self.assertIsNotNone(self.protocol._manual_password_re)
        self.assertIsNotNone(self.protocol._manual_login_error_re)

        # -- restore_device_context() raises when the stack is empty --
        self.assertRaises(ProtocolException, self.protocol.restore_device_context)

    def testRestoreDeviceContext(self):
        pass  # Tested in full detail by testSwitchDeviceContext().

    def testClose(self):
        if self.protocol.__class__ == Protocol:
            return
        self.doLogin()
        self.protocol.execute('ls')
        driver = self.protocol.get_driver()
        if self.protocol._logout.__func__ is Protocol._logout:
            # Base _logout delegates to driver.logout() — verify the full chain.
            with unittest.mock.patch.object(driver, 'logout') as mock_driver_logout:
                self.protocol.close(force=True)
                mock_driver_logout.assert_not_called()
        else:
            # Subclass overrides _logout — verify it is not called by close().
            with unittest.mock.patch.object(self.protocol, '_logout') as mock_logout:
                self.protocol.close(force=True)
                mock_logout.assert_not_called()
        self.assertEqual(0, self.protocol._buffer.size())
        self.assertEqual('unknown', self.protocol.guess_os())
        self.assertEqual(0, self.protocol.stdout.tell())
        self.assertFalse(self.protocol.connected)
        self.assertTrue(self.protocol.response is not None)

    def testGracefulClose(self):
        if self.protocol.__class__ == Protocol:
            return
        self.doLogin()
        self.protocol.execute('ls')
        driver = self.protocol.get_driver()
        if self.protocol._logout.__func__ is Protocol._logout:
            # Base _logout delegates to driver.logout() — verify the full chain.
            with unittest.mock.patch.object(driver, 'logout') as mock_driver_logout:
                self.protocol.close(force=False)
                mock_driver_logout.assert_called_once()
        else:
            # Subclass overrides _logout — verify it is called by close().
            with unittest.mock.patch.object(self.protocol, '_logout') as mock_logout:
                self.protocol.close(force=False)
                mock_logout.assert_called_once()
        self.assertEqual(0, self.protocol._buffer.size())
        self.assertEqual('unknown', self.protocol.guess_os())
        self.assertEqual(0, self.protocol.stdout.tell())
        self.assertFalse(self.protocol.connected)
        self.assertTrue(self.protocol.response is not None)

    def testReconnect(self):
        # Test can not work on the abstract base.
        if self.protocol.__class__ == Protocol:
            return

        # Assign a logfile before the first connect.
        # No FD should be open yet — the file is only opened on connect().
        fd, logpath = tempfile.mkstemp(suffix='.log')
        os.close(fd)
        self.addCleanup(os.unlink, logpath)
        self.protocol.logfile = logpath
        self.assertIsNone(self.protocol._log)

        # --- First session ---
        self.doLogin()
        self.assertTrue(self.protocol._log is not None)  # FD opened by connect()
        self.protocol.execute('ls')
        first_response = self.protocol.response
        self.assertTrue(first_response is not None)
        self.assertTrue(first_response.startswith('ls'))
        self.assertTrue(self.protocol.is_app_authenticated())
        self.assertTrue(self.protocol.is_app_authorized())
        self.assertEqual('shell', self.protocol.guess_os())

        self.protocol.close(force=True)

        # close() resets session state; response and logfile path are preserved.
        self.assertFalse(self.protocol._connected)
        self.assertIsNone(self.protocol._log)           # FD closed by _reset()
        self.assertEqual(logpath, self.protocol.logfile) # path survives close
        self.assertEqual(0, self.protocol._buffer.size())
        self.assertEqual('unknown', self.protocol.guess_os())
        self.assertFalse(self.protocol.is_app_authenticated())
        self.assertFalse(self.protocol.is_app_authorized())
        self.assertEqual(first_response, self.protocol.response)

        # First session data must have been flushed to disk.
        with open(logpath) as f:
            first_log_size = len(f.read())
        self.assertGreater(first_log_size, 0)

        # --- Second session on the same instance (reconnect) ---
        self.doLogin()
        self.assertTrue(self.protocol._log is not None)  # FD reopened by connect()
        self.protocol.execute('ls')
        second_response = self.protocol.response
        self.assertTrue(second_response is not None)
        self.assertTrue(second_response.startswith('ls'))
        self.assertTrue(self.protocol.is_app_authenticated())
        self.assertTrue(self.protocol.is_app_authorized())
        self.assertEqual('shell', self.protocol.guess_os())

        self.protocol.close(force=True)

        self.assertIsNone(self.protocol._log)
        self.assertEqual(logpath, self.protocol.logfile)

        # Second session appended to the same logfile.
        with open(logpath) as f:
            second_log_size = len(f.read())
        self.assertGreater(second_log_size, first_log_size)


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(ProtocolTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
