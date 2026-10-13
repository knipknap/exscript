import sys
import unittest
import os.path
import subprocess

basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


class scriptsTest(unittest.TestCase):

    def run_script(self, name, *args):
        env = dict(os.environ)
        pythonpath = [basedir]
        if env.get('PYTHONPATH'):
            pythonpath.append(env['PYTHONPATH'])
        env['PYTHONPATH'] = os.pathsep.join(pythonpath)
        script = os.path.join(basedir, 'scripts', name)
        proc = subprocess.Popen([sys.executable, script] + list(args),
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                env=env)
        stdout, stderr = proc.communicate()
        return proc.returncode, stdout.decode('utf8'), stderr.decode('utf8')

    def testExscriptHelp(self):
        code, stdout, stderr = self.run_script('exscript', '--help')
        self.assertEqual(code, 0, stderr)
        self.assertIn('--load-driver', stdout)


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(scriptsTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
