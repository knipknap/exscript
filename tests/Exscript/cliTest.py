import contextlib
import io
import unittest
from unittest import mock

from Exscript.cli import _duration, _expand_bracket, otp_main
from Exscript.util.crypt import otp


class cliTest(unittest.TestCase):
    def testDuration(self):
        self.assertEqual(_duration(''), 0)
        self.assertEqual(_duration('90'), 90)
        self.assertEqual(_duration('1.5m'), 90)
        self.assertEqual(_duration('1h 30m'), 5400)
        self.assertEqual(_duration('2d'), 172800)
        for invalid in 'tomorrow', '1x', '-1', '1; rm -rf ~':
            self.assertRaises(ValueError, _duration, invalid)

    def testPromptValuesAreLiteralsOnly(self):
        cases = {
            '[1, 2]': [1, 2],
            '42': 42,
            'plain text': 'plain text',
            '__import__("os").getcwd()': '__import__("os").getcwd()',
        }
        for typed, expected in cases.items():
            with mock.patch('builtins.input', return_value=typed):
                self.assertEqual(_expand_bracket('count', '{#count}'), expected)

    def testOtp(self):
        stdout = io.StringIO()
        with (
            mock.patch('getpass.getpass', return_value='password') as getpass,
            contextlib.redirect_stdout(stdout),
        ):
            self.assertEqual(otp_main(['9999', 'abc123']), 0)
        getpass.assert_called_once_with('Password: ')
        self.assertEqual(stdout.getvalue(), otp('password', 'abc123', 9999) + '\n')
        self.assertEqual(stdout.getvalue(), 'ACTA AMMO CAR WEB BIN YAP\n')

    def testOtpWithoutNumber(self):
        stderr = io.StringIO()
        with (
            mock.patch('getpass.getpass') as getpass,
            contextlib.redirect_stderr(stderr),
            self.assertRaises(SystemExit) as cm,
        ):
            otp_main(['abc', 'abc123'])
        self.assertEqual(cm.exception.code, 2)
        self.assertIn('first argument must be a number', stderr.getvalue())
        getpass.assert_not_called()
