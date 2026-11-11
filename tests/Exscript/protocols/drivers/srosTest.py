"""
The sros driver, with the banner, the prompts and the messages of Nokia
(Alcatel-Lucent) SR OS.
"""

import unittest

from Exscript.protocols.drivers import driver_map
from Exscript.protocols.exception import InvalidCommandException

from .device import ACCOUNT, Device, banner, connect, search


class SROSDriverTest(unittest.TestCase):
    def setUp(self):
        self.driver = driver_map['sros']

    def testCheckHeadForOs(self):
        self.assertEqual(self.driver.check_head_for_os(banner('sros').rstrip('\n')), 95)
        self.assertEqual(self.driver.check_head_for_os('\r\nRouter#'), 0)

    def testPrompts(self):
        # The prompt shows the active CPM (A or B), the context, and an
        # asterisk for unsaved changes.
        prompts = (
            'A:sros-pe1# ',
            '*A:sros-pe1# ',
            'B:sros-pe1>config# ',
            'A:sros-pe1>config>router# ',
            '*A:sros-pe1>config>service>vprn$ ',
        )
        for prompt in prompts:
            self.assertTrue(search(self.driver.prompt_re, 'Done\r\n' + prompt), prompt)
        self.assertFalse(search(self.driver.prompt_re, '\r\nsros-pe1# '))

    def testLogin(self):
        device = Device(
            'A:sros-pe1# ', banner=banner('sros').split('Login')[0], login=('Login: ', 'Password: ')
        )
        conn = connect(self, device, 'sros', login=ACCOUNT)
        self.assertEqual(device.received, ['admin', 'login-secret'])
        self.assertTrue(conn.is_app_authorized())

    def testInitTerminal(self):
        device = Device('A:sros-pe1# ')
        conn = connect(self, device, 'sros')
        conn.autoinit()
        expected = [
            'environment no more',
            'environment reduced-prompt 2',
            'environment no saved-ind-prompt',
        ]
        self.assertEqual(device.received, expected)

    def testError(self):
        device = Device('A:sros-pe1# ')
        device.add_command('shw', '\r\nError: Bad command.')
        conn = connect(self, device, 'sros')
        self.assertRaises(InvalidCommandException, conn.execute, 'shw router interface')

    def testLogout(self):
        device = Device('A:sros-pe1# ')
        conn = connect(self, device, 'sros')
        self.driver.logout(conn)
        self.assertEqual(device.received, ['logout'])


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(SROSDriverTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
