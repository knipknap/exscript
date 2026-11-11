"""
The bigip driver, with the banner and the prompt of the TMSH shell of an F5
BIG-IP.
"""

import unittest

from Exscript.protocols.drivers import driver_map
from Exscript.protocols.exception import InvalidCommandException

from .device import ACCOUNT, Device, banner, connect, search

PROMPT = 'admin@(bigip1)(cfg-sync Standalone)(Active)(/Common)(tmos)# '


class BigIPDriverTest(unittest.TestCase):
    def setUp(self):
        self.driver = driver_map['bigip']

    def testCheckHeadForOs(self):
        self.assertEqual(self.driver.check_head_for_os(banner('bigip.1')), 90)
        self.assertEqual(self.driver.check_head_for_os('\r\n[admin@bigip1:Active] ~ # '), 0)

    def testPrompts(self):
        prompts = PROMPT, 'admin@(bigip1)(cfg-sync In Sync)(Active)(/Common)(tmos.ltm)# '
        for prompt in prompts:
            self.assertTrue(search(self.driver.prompt_re, 'Last login\r\n' + prompt), prompt)
        self.assertFalse(search(self.driver.prompt_re, '\r\n[admin@bigip1:Active] ~ # '))  # bash

    def testNoAuthorization(self):
        # The role of the user grants the privileges.
        device = Device(PROMPT)
        conn = connect(self, device, 'bigip')
        conn.auto_app_authorize(ACCOUNT)
        self.assertEqual(device.received, [])

    def testInitTerminal(self):
        device = Device(PROMPT)
        conn = connect(self, device, 'bigip')
        conn.autoinit()
        self.assertEqual(device.received, ['modify cli preference pager disabled'])

    def testError(self):
        device = Device(PROMPT)
        device.add_command('list ltm pol', '\r\nSyntax Error: "pol" unknown property')
        conn = connect(self, device, 'bigip')
        self.assertRaises(InvalidCommandException, conn.execute, 'list ltm pol')


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(BigIPDriverTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
