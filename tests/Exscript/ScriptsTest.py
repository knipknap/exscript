import os
import selectors
import signal
import subprocess
import sys
import tempfile
import time
import unittest

import Exscript

BASEDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
KEYFILE = os.path.join(BASEDIR, 'tests', 'Exscript', 'protocols', 'id_rsa')

# Runs the CLI, but getpass.getuser() finds no user name, as for a user ID without a passwd
# entry: it raises OSError since Python 3.13, and KeyError before.
WITHOUT_USER_NAME = '''
import getpass, sys

from Exscript.cli import main


def getuser():
    raise %s('no user name')


getpass.getuser = getuser
sys.exit(main())
'''


class ScriptsTest(unittest.TestCase):
    """Runs the exscript command line tool like a user."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.env = dict(
            os.environ, HOME=self.tmpdir.name, USERPROFILE=self.tmpdir.name, NO_COLOR='1'
        )

    def run_exscript(self, *args, python_args=('-m', 'Exscript')):
        proc = subprocess.run(  # noqa: S603 - runs Exscript with fixed arguments
            [sys.executable, *python_args, *args],
            capture_output=True,
            encoding='utf-8',
            env=self.env,
            timeout=60,
        )
        return proc.returncode, proc.stdout + proc.stderr

    def read_until(self, pipe, marker, timeout=30):
        """Reads from the given pipe until the given marker, and returns what it read."""
        data = b''
        deadline = time.monotonic() + timeout
        with selectors.DefaultSelector() as selector:
            selector.register(pipe, selectors.EVENT_READ)
            while marker not in data:
                if not selector.select(deadline - time.monotonic()):
                    self.fail(f'no {marker!r} within {timeout} seconds: {data!r}')
                chunk = os.read(pipe.fileno(), 4096)
                if not chunk:
                    self.fail(f'no {marker!r} before the end of the output: {data!r}')
                data += chunk
        return data

    def write_template(self, text):
        path = os.path.join(self.tmpdir.name, 'test.exscript')
        with open(path, 'w', encoding='utf-8') as fp:
            fp.write(text)
        return path

    def testHelp(self):
        code, output = self.run_exscript('--help')
        self.assertEqual(code, 0, output)
        self.assertTrue(output.startswith('usage: exscript '), output)
        for option in '--load-driver', '--insecure', '--ssh-host-key-policy':
            self.assertIn(option, output)

    def testVersion(self):
        code, output = self.run_exscript('--version')
        self.assertEqual(code, 0, output)
        self.assertEqual(output, Exscript.__version__ + '\n')

    def testRunTemplate(self):
        template = self.write_template('{sys.message("hello")}\n')
        args = '--non-interactive', '--no-authentication', template, 'dummy://r1'
        code, output = self.run_exscript(*args)
        self.assertEqual(code, 0, output)
        self.assertIn('hello', output)

    def testSecureModeByDefault(self):
        template = self.write_template('{sys.env("PATH")}\n')
        args = '--non-interactive', '--no-authentication', template, 'dummy://r1'
        code, output = self.run_exscript(*args)
        self.assertEqual(code, 2, output)
        self.assertIn("insecure function 'sys.env' is not permitted", output)

        code, output = self.run_exscript('--insecure', *args)
        self.assertEqual(code, 0, output)

    def testSshKeyWithoutUserName(self):
        # Without a login, the key is for the current user; without a name, it gets no account.
        template = self.write_template('{sys.message("hello")}\n')
        args = '--non-interactive', '--no-authentication', '--ssh-key', KEYFILE, template
        for error in 'OSError', 'KeyError':
            python_args = '-c', WITHOUT_USER_NAME % error
            code, output = self.run_exscript(*args, 'dummy://r1', python_args=python_args)
            self.assertEqual(code, 0, output)
            self.assertIn('hello', output)

    @unittest.skipIf(sys.platform == 'win32', 'Windows cannot send SIGINT to a process')
    def testCtrlC(self):
        # The job waits for a minute in a thread, which Ctrl+C cannot interrupt.
        template = self.write_template('{sys.message("started")}{sys.wait(60)}\n')
        args = '--non-interactive', '--no-authentication', template, 'dummy://h1'
        proc = subprocess.Popen(  # noqa: S603 - runs Exscript with fixed arguments
            [sys.executable, '-u', '-m', 'Exscript', *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.env,
        )
        self.addCleanup(proc.stderr.close)
        self.addCleanup(proc.stdout.close)
        self.addCleanup(proc.wait)
        self.addCleanup(proc.kill)
        output = self.read_until(proc.stdout, b'started')

        proc.send_signal(signal.SIGINT)
        stdout, stderr = proc.communicate(timeout=10)
        self.assertEqual(proc.returncode, 130, output + stdout + stderr)
        self.assertIn(b'Interrupted.', stderr)


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(ScriptsTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
