"""
The eos driver, with the banners, the prompts and the messages of Arista EOS.
"""

import unittest

from Exscript.protocols.drivers import driver_map
from Exscript.protocols.exception import InvalidCommandException

from .device import ACCOUNT, Device, banner, connect, search


class EOSDriverTest(unittest.TestCase):
    def setUp(self):
        self.driver = driver_map['eos']

    def testPrompts(self):
        prompts = (
            'switch>',
            'switch#',
            'switch(config)#',
            'switch(config-if-Et1)#',
            'hostname(s1)#',
            'switch(vrf:blah)(config)#',
        )
        for prompt in prompts:
            self.assertTrue(search(self.driver.prompt_re, 'Last login\r\n' + prompt), prompt)
        # EOS sends no line break before the first prompt.
        self.assertTrue(search(self.driver.prompt_re, 'switch>'))

    def testLoginPatterns(self):
        self.assertTrue(search(self.driver.user_re, banner('eos.1').split('testuser')[0]))
        self.assertTrue(search(self.driver.password_re, 'testuser\r\npassword:'))
        for error in '% Bad secrets', 'Login incorrect':
            self.assertTrue(search(self.driver.login_error_re, 'Password:\r\n' + error), error)

    def testLoginAndEnable(self):
        device = Device(
            'switch>',
            banner='---\r\nThis is a login banner\r\n---\r\n',
            login=('switch login: ', 'Password: '),
            enabled_prompt='switch#',
        )
        conn = connect(self, device, 'eos', login=ACCOUNT)
        self.assertEqual(device.received, ['admin', 'login-secret', 'enable', 'enable-secret'])
        self.assertTrue(conn.is_app_authorized())

    def testInitTerminal(self):
        device = Device('switch#')
        conn = connect(self, device, 'eos')
        conn.autoinit()
        self.assertEqual(device.received, ['terminal dont-ask', 'terminal length 0'])

    def testErrors(self):
        device = Device('switch#')
        device.add_command('show vlna', "\r\n% Invalid input")
        device.add_command('show ip', "\r\n% Incomplete command")
        device.add_command('sh', "\r\n% Ambiguous command")
        conn = connect(self, device, 'eos')
        for command in 'show vlna', 'show ip', 'sh':
            with self.subTest(command=command):
                self.assertRaises(InvalidCommandException, conn.execute, command)


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(EOSDriverTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
