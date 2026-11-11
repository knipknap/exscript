"""
The ios_xr driver, with the prompts of Cisco IOS XR.
"""

import unittest

from Exscript.protocols.drivers import driver_map

from .device import ACCOUNT, Device, banner, connect, search

PROMPT = 'RP/0/RSP0/CPU0:xr-pe1#'


class IOSXRDriverTest(unittest.TestCase):
    def setUp(self):
        self.driver = driver_map['ios_xr']

    def testCheckResponseForOs(self):
        self.assertEqual(self.driver.check_response_for_os(banner('ios_xr')), 95)
        self.assertEqual(self.driver.check_response_for_os('\r\nRouter#'), 0)

    def testCheckNetconfCapabilities(self):
        capabilities = (
            'urn:ietf:params:netconf:base:1.1\n'
            'http://cisco.com/ns/yang/Cisco-IOS-XR-ifmgr-cfg?module=Cisco-IOS-XR-ifmgr-cfg'
            '&revision=2017-09-07\n'
        )
        self.assertEqual(self.driver.check_netconf_capabilities(capabilities), 100)
        self.assertEqual(self.driver.check_netconf_capabilities(capabilities.split('\n')[0]), 0)

    def testPrompts(self):
        prompts = (
            PROMPT,
            'RP/0/RP0/CPU0:xr-pe1(config)#',
            'RP/0/RP0/CPU0:xr-pe1(config-if)#',
            'RP/0/0/CPU0:ios#',  # IOS XRv
        )
        for prompt in prompts:
            self.assertTrue(
                search(self.driver.prompt_re, 'Thu Nov 10 12:00:00.000 UTC\r\n' + prompt)
            )
        self.assertFalse(search(self.driver.prompt_re, '\r\nRouter#'))

    def testLogin(self):
        device = Device(PROMPT, login=('Username: ', 'Password: '))
        conn = connect(self, device, 'ios_xr', login=ACCOUNT)
        self.assertEqual(device.received, ['admin', 'login-secret'])
        self.assertTrue(conn.is_app_authorized())

    def testInitTerminal(self):
        device = Device(PROMPT)
        conn = connect(self, device, 'ios_xr')
        conn.autoinit()
        expected = ['terminal exec prompt no-timestamp', 'terminal len 0', 'terminal width 0']
        self.assertEqual(device.received, expected)


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(IOSXRDriverTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
