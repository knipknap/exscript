import os
import re
import unittest

from Exscript import Account
from Exscript.emulators import VirtualDevice
from Exscript.protocols import Dummy, drivers
from Exscript.protocols.drivers import isam
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


def suite():
    loader = unittest.TestLoader()
    return unittest.TestSuite(
        [loader.loadTestsFromTestCase(OsGuesserTest), loader.loadTestsFromTestCase(SignalTest)]
    )


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
