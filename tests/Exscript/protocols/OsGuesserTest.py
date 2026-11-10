import os
import re
import unittest

from Exscript import Account
from Exscript.emulators import VirtualDevice
from Exscript.protocols import Dummy, drivers
from Exscript.protocols.drivers import isam
from Exscript.protocols.exception import LoginFailure
from Exscript.protocols.osguesser import OsGuesser


class OsGuesserTest(unittest.TestCase):
    CORRELATE = OsGuesser

    def setUp(self):
        self.sa = OsGuesser()

    def testConstructor(self):
        osg = OsGuesser()
        self.assertIsInstance(osg, OsGuesser)

    def testReset(self):
        self.testSet()
        self.sa.reset()
        self.testSet()

    def testSet(self):
        self.assertEqual(self.sa.get('test'), None)
        self.assertEqual(self.sa.get('test', 0), None)
        self.assertEqual(self.sa.get('test', 50), None)
        self.assertEqual(self.sa.get('test', 100), None)

        self.sa.set('test', 'foo', 0)
        self.assertEqual(self.sa.get('test'), 'foo')
        self.assertEqual(self.sa.get('test', 0), 'foo')
        self.assertEqual(self.sa.get('test', 10), None)

        self.sa.set('test', 'foo', 10)
        self.assertEqual(self.sa.get('test'), 'foo')
        self.assertEqual(self.sa.get('test', 0), 'foo')
        self.assertEqual(self.sa.get('test', 10), 'foo')
        self.assertEqual(self.sa.get('test', 11), None)

        self.sa.set('test', 'foo', 5)
        self.assertEqual(self.sa.get('test'), 'foo')
        self.assertEqual(self.sa.get('test', 0), 'foo')
        self.assertEqual(self.sa.get('test', 10), 'foo')
        self.assertEqual(self.sa.get('test', 11), None)

    def testSetFromMatch(self):
        match_list = (
            (re.compile('on'), 'uno', 50),
            (re.compile('two'), 'doe', 0),
            (re.compile('one'), 'eins', 90),
        )
        self.assertEqual(self.sa.get('test'), None)

        self.sa.set_from_match('test', match_list, '2two2')
        self.assertEqual(self.sa.get('test'), 'doe')

        self.sa.set_from_match('test', match_list, '2one2')
        self.assertEqual(self.sa.get('test'), 'eins')

    def testGet(self):
        pass  # See testSet().

    def testCheckReceivedData(self):
        dirname = os.path.dirname(__file__)
        banner_dir = os.path.join(dirname, 'banners')
        for file in os.listdir(banner_dir):
            if file.startswith('.'):
                continue
            osname = file.split('.')[0]
            if not drivers.driver_map[osname].supports_os_guesser():
                continue
            file = os.path.join(banner_dir, file)
            with open(file, encoding='utf-8') as fp:
                banner = fp.read().rstrip('\n')
            osg = OsGuesser()
            for char in banner:
                osg.check_received_data(char, False)
            self.assertEqual(osg.get('os'), osname)

    def testCheckProtocolInfo(self):
        osg = OsGuesser()
        osg.check_protocol_info('')
        self.assertEqual(osg.get('os'), "unknown")
        osg.check_protocol_info(None)
        self.assertEqual(osg.get('os'), "unknown")
        osg.check_protocol_info("SSH-2.0-Cisco-1.25")
        self.assertEqual(osg.get('os'), "ios")

    def testCheckNetconfCapabilities(self):
        osg = OsGuesser()
        osg.check_netconf_capabilities(
            [
                'urn:ietf:params:netconf:base:1.0',
                'urn:ietf:params:netconf:capability:candidate:1.0',
                'urn:ietf:params:netconf:capability:confirmed-commit:1.0',
                'http://xml.juniper.net/netconf/junos/1.0',
            ]
        )
        self.assertEqual(osg.get('os'), "junos")

    def testCheckNetconfCapabilitiesAsText(self):
        osg = OsGuesser()
        osg.check_netconf_capabilities(None)
        osg.check_netconf_capabilities([])
        self.assertEqual(osg.get('os'), 'unknown')
        osg.check_netconf_capabilities(
            'urn:ietf:params:netconf:base:1.0\nhttp://xml.juniper.net/netconf/junos/1.0'
        )
        self.assertEqual(osg.get('os'), 'junos')

    def testSetWithoutValue(self):
        self.sa.set('os', 'ios', 50)
        self.sa.set('os', None, 100)  # ignored
        self.assertEqual(self.sa.get('os', 50), 'ios')


def guess(head='', response='', protocol_info=''):
    """Returns the guess after the given data, fed one character per read (the worst case)."""
    guesser = OsGuesser()
    guesser.check_protocol_info(protocol_info)
    for char in head:
        guesser.check_received_data(char, False)
    for char in response:
        guesser.check_received_data(char, True)
    return guesser.get('os')


class SignalTest(unittest.TestCase):
    """Weak signals must not claim what other systems print, too."""

    def testLastLoginIsNoSign(self):
        # Linux, EOS, IOS XR and many others print it, so no driver may claim it.
        last_login = '\r\nLast login: Mon Oct 26 10:00:00 2026 from 192.0.2.1\r\n'
        self.assertEqual(guess(head=last_login), 'unknown')
        self.assertEqual(guess(response=last_login + 'switch>'), 'unknown')

    def testLoginPrompt(self):
        self.assertEqual(guess(head='\r\nrouter3 login: '), 'shell')  # Linux, BusyBox
        self.assertEqual(guess(head='\r\nrouter1 (ttyp0)\r\n\r\nlogin: '), 'junos')

    def testShellPrompt(self):
        for prompt in 'router1:~$ ', 'admin@router1:/etc# ', '\x1b[?2004hrouter1:~$ ':
            self.assertEqual(guess(response='\r\nuname\r\nLinux\r\n' + prompt), 'shell', prompt)
        for prompt in 'router#', 'RP/0/RSP0/CPU0:xr-pe1#', 'A:sros-pe1#', 'admin@junos-mx> ':
            self.assertNotEqual(guess(response='\r\nshow\r\n' + prompt), 'shell', prompt)

    def testNxosBanner(self):
        # Newer NX-OS versions, e.g. nx-osv9000, print the short name.
        self.assertEqual(guess(head='Cisco NX-OS Software\r\n'), 'nxos')
        banner = 'Cisco Nexus Operating System (NX-OS) Software\r\n'
        self.assertEqual(guess(head=banner), 'nxos')

    def testIsamPrompt(self):
        self.assertEqual(guess(response='\r\ninfo\r\ntyp:isadmin>#'), 'isam')
        for prompt in 'router#', 'switch>', 'hostname >', 'S>* 10.0.0.0/8 is directly connected':
            self.assertEqual(guess(response='\r\nshow\r\n' + prompt), 'unknown', prompt)

    def testIsamUsesItsErrorPatterns(self):
        self.assertIs(drivers.driver_map['isam'].error_re, isam._error_re)

    def testLastLoginLineDoesNotBreakLogin(self):
        device = VirtualDevice(
            'host',
            login_type=VirtualDevice.LOGIN_TYPE_NONE,
            strict=False,
            banner='Welcome\nLast login: Mon Oct 26 10:00:00 2026 from 192.0.2.1\n',
        )
        device.set_prompt('user@host:~$ ')
        device.add_command('uname', 'Linux')
        conn = Dummy(device=device)
        conn.connect('host')
        conn.login(Account('user', 'password', needs_lock=False))
        conn.execute('uname')
        self.assertEqual(conn.get_response().strip(), 'Linux')


class AcmeDriver(drivers.Driver):
    """The custom driver of the documentation (docs/drivers.rst)."""

    def __init__(self):
        drivers.Driver.__init__(self, 'acme')
        self.prompt_re = [re.compile(r'[\r\n]acme-[\w-]+[>#] ?$')]

    def check_head_for_os(self, string):
        if 'Acme Networks OS' in string:
            return 90
        return 0

    def init_terminal(self, conn):
        conn.execute('terminal length 0')


class DriverRegistryTest(unittest.TestCase):
    def setUp(self):
        self.sent = []
        self.device = VirtualDevice(
            'acme-pe1', login_type=VirtualDevice.LOGIN_TYPE_NONE, banner='Acme Networks OS 1.0\n'
        )
        self.device.add_command(
            'terminal length 0', lambda command: self.sent.append(command) or ''
        )

    def tearDown(self):
        if 'acme' in drivers.driver_map:
            drivers.disable_driver('acme')

    def login(self):
        conn = Dummy(device=self.device)
        conn.connect('acme-pe1')
        conn.login(Account('user', 'password', needs_lock=False))
        return conn

    def testAddDriver(self):
        drivers.add_driver(AcmeDriver)
        conn = self.login()
        self.assertEqual(conn.guess_os(), 'acme')
        self.assertIsInstance(conn.get_driver(), AcmeDriver)
        conn.autoinit()
        self.assertEqual(len(self.sent), 1)

    def testDisableDriver(self):
        drivers.add_driver(AcmeDriver)
        drivers.disable_driver('acme')
        self.assertNotIn('acme', drivers.driver_map)
        self.assertNotIn(AcmeDriver, drivers.driver_classes)
        self.assertNotIn('acme', [driver.name for driver in drivers.drivers])
        self.assertEqual(self.login().guess_os(), 'unknown')
        self.assertRaises(TypeError, Dummy().set_driver, 'acme')

    def testPatternsAreCompiled(self):
        # The protocol calls search() on each pattern; a string would fail
        # with an AttributeError during the login.
        attributes = 'user_re', 'password_re', 'prompt_re', 'error_re', 'login_error_re'
        for name, driver in drivers.driver_map.items():
            for attribute in attributes:
                for pattern in getattr(driver, attribute):
                    self.assertIsInstance(pattern, re.Pattern, f'{name}.{attribute}')

    def testLoginFailureOverEricssonBan(self):
        device = VirtualDevice('ban1', login_type=VirtualDevice.LOGIN_TYPE_NONE, strict=False)
        device.set_prompt('Login failed\n')
        conn = Dummy(device=device, driver='ericsson_ban', timeout=1)
        conn.connect('ban1')
        self.addCleanup(conn.close, True)
        conn.send('admin\r')
        self.assertRaises(
            LoginFailure, conn.app_authenticate, Account('admin', 'x', needs_lock=False)
        )


def suite():
    loader = unittest.TestLoader()
    return unittest.TestSuite(
        [
            loader.loadTestsFromTestCase(OsGuesserTest),
            loader.loadTestsFromTestCase(SignalTest),
            loader.loadTestsFromTestCase(DriverRegistryTest),
        ]
    )


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
