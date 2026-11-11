"""
The cienasaos driver, with the banner and the prompt of a Ciena SAOS switch.
"""

import unittest

from Exscript.protocols.drivers import driver_map
from Exscript.protocols.exception import InvalidCommandException

from .device import ACCOUNT, Device, banner, connect


class CienaSAOSDriverTest(unittest.TestCase):
    def setUp(self):
        self.driver = driver_map['cienasaos']

    def testCheckHeadForOs(self):
        self.assertEqual(self.driver.check_head_for_os(banner('cienasaos.1')), 90)
        self.assertEqual(self.driver.check_head_for_os('\r\nsaos-5160 login: '), 0)

    def testLogin(self):
        device = Device('saos-5160> ', login=('saos-5160 login: ', 'Password:'))
        conn = connect(self, device, 'cienasaos', login=ACCOUNT)
        self.assertEqual(device.received, ['admin', 'login-secret'])
        self.assertTrue(conn.is_app_authorized())

    def testInitTerminal(self):
        device = Device('saos-5160> ')
        conn = connect(self, device, 'cienasaos')
        conn.autoinit()
        self.assertEqual(device.received, ['system shell session set more off'])

    def testError(self):
        device = Device('saos-5160> ')
        device.add_command('port shw', "\r\nSHELL PARSER FAILURE: 'shw' - no valid completion")
        conn = connect(self, device, 'cienasaos')
        self.assertRaises(InvalidCommandException, conn.execute, 'port shw')


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(CienaSAOSDriverTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
