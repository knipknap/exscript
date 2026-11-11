import os
import selectors
import signal
import subprocess
import sys
import tempfile
import time
import unittest

import Exscript


class ScriptsTest(unittest.TestCase):
    """Runs the exscript command line tool like a user."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        # UTF-8 output also where the locale encoding is another, e.g. on Windows.
        self.env = dict(
            os.environ,
            HOME=self.tmpdir.name,
            USERPROFILE=self.tmpdir.name,
            NO_COLOR='1',
            PYTHONIOENCODING='utf-8',
        )

    def run_exscript(self, *args):
        proc = subprocess.run(  # noqa: S603 - runs Exscript with fixed arguments
            [sys.executable, '-m', 'Exscript', *args],
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
