import os
import subprocess
import sys
import tempfile
import unittest

BASEDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SCRIPT = os.path.join(BASEDIR, 'scripts', 'exscript')


class ScriptsTest(unittest.TestCase):
    """Runs the exscript command line tool like a user."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)

    def run_exscript(self, *args):
        env = dict(os.environ, HOME=self.tmpdir.name, USERPROFILE=self.tmpdir.name)
        proc = subprocess.run(  # noqa: S603 - runs this repository's script with fixed arguments
            [sys.executable, SCRIPT, *args],
            capture_output=True,
            encoding='utf-8',
            env=env,
            timeout=60,
        )
        return proc.returncode, proc.stdout + proc.stderr

    def write_template(self, text):
        path = os.path.join(self.tmpdir.name, 'test.exscript')
        with open(path, 'w', encoding='utf-8') as fp:
            fp.write(text)
        return path

    def testHelp(self):
        code, output = self.run_exscript('--help')
        self.assertEqual(code, 0, output)
        for option in '--load-driver', '--insecure', '--ssh-host-key-policy':
            self.assertIn(option, output)

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


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(ScriptsTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
