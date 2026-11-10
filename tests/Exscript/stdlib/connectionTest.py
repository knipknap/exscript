import unittest
from unittest import mock

from interpreter.helpers import RecordingDevice, TemplateTestCase, split_error

import Exscript.stdlib.connection
from Exscript import Account
from Exscript.emulators import VirtualDevice
from Exscript.parselib.exception import ExecuteError
from Exscript.protocols import Dummy
from Exscript.protocols.exception import InvalidCommandException


class connectionTest(TemplateTestCase):
    """
    The functions of the template language that use the connection.
    """

    CORRELATE = Exscript.stdlib.connection

    def setUp(self):
        super().setUp()
        self.device.add_command('bad', '% Invalid input detected')
        self.device.add_command('reload', 'Proceed with reload? [confirm]', prompt=False)

    def useLoginDevice(self, login=True):
        """
        Connects to a device that asks for a user name and a password, logs
        in as admin with the password "secret" unless login is False, and
        forgets the commands of the login.
        """
        device = RecordingDevice(login_type=VirtualDevice.LOGIN_TYPE_BOTH)
        device.add_command('enable', 'Password: ', prompt=False)
        device.add_command('relogin', lambda command: device.init(), prompt=False)
        self.device = device
        self.conn = Dummy(device=device, timeout=5)
        self.conn.connect('r1')
        self.addCleanup(self.conn.close, force=True)
        if login:
            self.conn.login(Account('admin', 'secret'))
        del device.received[:]

    def testAuthenticate(self):
        self.useLoginDevice()
        variables = self.evaluate(
            '{connection.sendline("relogin")}{connection.authenticate()}\nls\n'
        )
        self.assertSent('relogin', 'admin', 'secret', 'ls')
        self.assertEqual(variables['__username__'], ['admin'])

    def testAuthenticateWithoutAccount(self):
        self.useLoginDevice(login=False)
        with self.assertRaises(ExecuteError) as cm:
            self.evaluate('{connection.authenticate()}')
        message = (
            "TypeError while executing function 'connection.authenticate':"
            ' An account is required in undefined:1'
        )
        self.assertEqual(split_error(cm.exception)[2], message)

    def testAuthenticateUser(self):
        self.useLoginDevice(login=False)
        self.evaluate('{connection.authenticate_user("admin", "secret")}\nls\n')
        self.assertSent('admin', 'secret', 'ls')
        self.assertTrue(self.conn.is_app_authenticated())

    def testAuthenticateUserAgain(self):
        self.useLoginDevice()
        self.evaluate('{connection.sendline("relogin")}{connection.authenticate_user()}\nls\n')
        self.assertSent('relogin', 'admin', 'secret', 'ls')

    def testAuthorize(self):
        self.useLoginDevice()
        text = (
            '{connection.sendline("enable")}{connection.authorize()}\n'
            '{connection.sendline("enable")}{connection.authorize("en")}\n'
            'ls\n'
        )
        self.evaluate(text)
        self.assertSent('enable', 'secret', 'enable', 'en', 'ls')
        self.assertTrue(self.conn.is_app_authorized())

    def testAutoAuthorize(self):
        # The IOS driver starts the authorization with "enable".
        self.useLoginDevice()
        self.conn.set_driver('ios')
        self.evaluate('{connection.auto_authorize()}\n{connection.auto_authorize("en")}\nls\n')
        self.assertSent('enable', 'secret', 'enable', 'en', 'ls')
        self.assertTrue(self.conn.is_app_authorized())

    def testAutoAuthorizeWithoutCommand(self):
        # The generic driver has no command to start the authorization.
        self.useLoginDevice()
        self.evaluate('{connection.sendline("enable")}{connection.auto_authorize("en")}\nls\n')
        self.assertSent('enable', 'en', 'ls')

    def testAutoinit(self):
        self.evaluate('{connection.autoinit()}')
        self.assertSent()
        self.conn.set_driver('ios')
        self.evaluate('{connection.autoinit()}')
        self.assertSent('term len 0', 'term width 0')

    def testClose(self):
        with mock.patch.object(self.conn, 'close', wraps=self.conn.close) as close:
            variables = self.evaluate('{connection.close()}')
        close.assert_called_once_with(force=False)
        self.assertFalse(self.conn.connected)
        self.assertEqual(variables['__response__'], [''])

        self.conn.connect('r1')
        with mock.patch.object(self.conn, 'close', wraps=self.conn.close) as close:
            self.evaluate('{connection.close(true)}')
        close.assert_called_once_with(force=True)
        self.assertFalse(self.conn.connected)

    def testExec_(self):
        variables = self.evaluate('{connection.exec("ls\\r")}')
        self.assertSent('ls')
        self.assertEqual(variables['__response__'], ['file1', 'file2'])
        variables = self.evaluate('{connection.exec(list.new("show version\\r", "ls\\r"))}')
        self.assertSent('ls', 'show version', 'ls')
        self.assertEqual(
            variables['__response__'], ['Version 1.0', 'Uptime 5 days', 'file1', 'file2']
        )

    def testExecline(self):
        variables = self.evaluate('{connection.execline("ls")}')
        self.assertSent('ls')
        self.assertEqual(variables['__response__'], ['file1', 'file2'])
        variables = self.evaluate(
            '{connection.execline(commands)}', commands=['show version', 'ls']
        )
        self.assertSent('ls', 'show version', 'ls')
        self.assertEqual(
            variables['__response__'], ['Version 1.0', 'Uptime 5 days', 'file1', 'file2']
        )

    def testExpect(self):
        variables = self.evaluate(
            '{connection.sendline("reload")}{connection.expect(/\\[confirm\\]/)}'
        )
        self.assertSent('reload')
        self.assertEqual(variables['__response__'], ['Proceed with reload? '])

    def testGetProtocol(self):
        self.assertEqual(self.evaluate('{x = connection.get_protocol()}')['x'], ['dummy'])

    def testGuessOs(self):
        self.assertEqual(self.evaluate('{x = connection.guess_os()}')['x'], ['unknown'])
        self.device.set_prompt('user@r1:~$ ')
        self.assertEqual(self.evaluate('ls\n{x = connection.guess_os()}')['x'], ['shell'])

    def testSend(self):
        variables = self.evaluate(
            '{connection.send("reload\\r")}{connection.send(list.new("y", "\\r"))}'
        )
        self.assertEqual(self.device.received, ['reload\r', 'y', '\r'])
        self.assertEqual(variables['__response__'], [''])

    def testSendline(self):
        self.evaluate('{connection.sendline("reload")}{connection.sendline(list.new("y", "n"))}')
        self.assertSent('reload', 'y', 'n')

    def testSetError(self):
        with self.assertRaises(InvalidCommandException):
            self.evaluate('{connection.set_error(/file2/)}ls\n')
        self.evaluate('{connection.set_error(/nothing/)}bad\n')
        with self.assertRaises(InvalidCommandException):
            self.evaluate('{connection.set_error()}bad\n')
        self.assertSent('ls', 'bad', 'bad')

    def testAddError(self):
        with self.assertRaises(InvalidCommandException):
            self.evaluate('{connection.add_error(/file2/)}ls\n')
        with self.assertRaises(InvalidCommandException):
            self.evaluate('{connection.add_error(/nothing/)}bad\n')
        self.assertSent('ls', 'bad')

    def testSetPrompt(self):
        variables = self.evaluate('{connection.set_prompt(/\\[confirm\\]/)}reload\n')
        self.assertEqual(variables['__response__'], ['Proceed with reload? '])
        variables = self.evaluate('{connection.set_prompt()}y\nls\n')
        self.assertSent('reload', 'y', 'ls')
        self.assertEqual(variables['__response__'], ['file1', 'file2'])

    def testAddPrompt(self):
        self.evaluate('{connection.add_prompt(/\\[confirm\\]/)}reload\ny\nls\n')
        self.assertSent('reload', 'y', 'ls')

    def testSetTimeout(self):
        self.evaluate('{connection.set_timeout(7)}')
        self.assertEqual(self.conn.get_timeout(), 7)
        self.evaluate('{connection.set_timeout("8")}')
        self.assertEqual(self.conn.get_timeout(), 8)

    def testWaitFor(self):
        text = '{connection.sendline("reload")}{connection.wait_for(/\\[confirm\\]/)}{connection.wait_for(/\\[confirm\\]/)}'
        variables = self.evaluate(text)
        self.assertSent('reload')
        self.assertEqual(variables['__response__'], ['Proceed with reload? '])


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(connectionTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
