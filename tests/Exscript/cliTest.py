import contextlib
import io
import os
import tempfile
import unittest
from unittest import mock

from Exscript.cli import _duration, _expand_bracket, main, otp_main
from Exscript.util import template
from Exscript.util.crypt import otp


class cliTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        # main() sets up the logging of the process and the debug level of the templates.
        for patcher in (
            mock.patch('Exscript.cli.setupLogging'),
            mock.patch.object(template, 'debug', 0),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def path(self, *names):
        """Returns the path of the given file in the temporary directory."""
        return os.path.join(self.tmpdir.name, *names)

    def write(self, name, text):
        """Writes the given text to the given file in the temporary directory."""
        with open(self.path(name), 'w', encoding='utf-8') as fp:
            fp.write(text)
        return self.path(name)

    def run_main(self, *args):
        """Runs main() with the given arguments, and returns the exit status and the output."""
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                code = main(list(args))
            except SystemExit as e:
                code = e.code
        return code, stdout.getvalue(), stderr.getvalue()

    def testHostFilesWithUserAndVariables(self):
        # The shell expands neither in quotes, e.g. --hosts '~/$SITE/hosts.txt'.
        os.mkdir(self.path('hosts'))
        self.write(os.path.join('hosts', 'hosts.txt'), 'dummy://r1\n')
        self.write(os.path.join('hosts', 'hosts.csv'), 'address\tgreeting\ndummy://r2\thello\n')
        env = {'HOME': self.tmpdir.name, 'USERPROFILE': self.tmpdir.name, 'SITE': 'hosts'}
        cases = (
            ('--hosts', 'hosts.txt', '{sys.message("hello")}'),
            ('--csv-hosts', 'hosts.csv', '{sys.message(greeting)}'),
        )
        with mock.patch.dict(os.environ, env):
            for option, name, script in cases:
                code, stdout, stderr = self.run_main(
                    '-n', '-i', '-e', script, option, '~/$SITE/' + name
                )
                self.assertEqual(code, 0, stderr)
                self.assertEqual(stdout, 'hello\n')

    def testDefineValueWithEqualSign(self):
        script = '{sys.message(a)}'
        code, stdout, stderr = self.run_main('-n', '-i', '-d', 'a=b=c', '-e', script, 'dummy://r1')
        self.assertEqual(code, 0, stderr)
        self.assertEqual(stdout, 'b=c\n')

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
