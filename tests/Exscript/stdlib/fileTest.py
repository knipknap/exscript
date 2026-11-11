import os
import stat
import tempfile
import unittest

from interpreter.helpers import TemplateTestCase, split_error

import Exscript.stdlib.file
from Exscript.parselib.exception import ExecuteError


class fileTest(TemplateTestCase):
    """
    The file functions of the template language. Except for file.exists(),
    they work only with secure=False.
    """

    CORRELATE = Exscript.stdlib.file

    def setUp(self):
        super().setUp()
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        self.tmpdir = tmpdir.name

    def path(self, *names):
        return os.path.join(self.tmpdir, *names)

    def run_insecure(self, text, **kwargs):
        return self.evaluate(text, secure=False, **kwargs)

    def write(self, name, text):
        with open(self.path(name), 'w', encoding='utf-8') as fp:
            fp.write(text)

    def read(self, name):
        with open(self.path(name), encoding='utf-8') as fp:
            return fp.read()

    def testChmod(self):
        self.write('a', 'a')
        self.write('b', 'b')
        paths = [self.path('a'), self.path('b')]
        self.addCleanup(lambda: [os.chmod(path, stat.S_IWRITE | stat.S_IREAD) for path in paths])
        self.run_insecure('{file.chmod(paths, 0400)}', paths=paths)
        for path in paths:
            self.assertEqual(os.stat(path).st_mode & 0o222, 0)  # read-only, also on Windows

    def testClear(self):
        self.write('a', 'old content\n')
        self.run_insecure('{file.clear(a)}{file.clear(b)}', a=self.path('a'), b=self.path('b'))
        self.assertEqual((self.read('a'), self.read('b')), ('', ''))

    def testExists(self):
        self.write('a', '')
        text = '{x = file.exists(a)}{y = file.exists(b)}{z = file.exists(both)}'
        paths = {'a': self.path('a'), 'b': self.path('b')}
        variables = self.evaluate(text, both=[paths['a'], paths['b']], **paths)
        self.assertEqual(
            (variables['x'], variables['y'], variables['z']), ([True], [False], [True, False])
        )

    def testMkdir(self):
        dirs = [self.path('a', 'b'), self.path('c')]
        self.run_insecure('{file.mkdir(dirs)}{file.mkdir(d, 0700)}', dirs=dirs, d=self.path('d'))
        for path in dirs + [self.path('d')]:
            self.assertTrue(os.path.isdir(path), path)
        if os.name != 'nt':
            self.assertEqual(os.stat(self.path('d')).st_mode & 0o777, 0o700)

    def testRead(self):
        self.write('a', 'line1\nline2\n')
        variables = self.run_insecure('{x = file.read(a)}', a=self.path('a'))
        self.assertEqual([line.rstrip('\n') for line in variables['x']], ['line1', 'line2'])
        self.assertEqual(variables['__response__'], variables['x'])

    def testReadAMissingFile(self):
        with self.assertRaises(ExecuteError) as cm:
            self.run_insecure('{x = file.read(a)}', a=self.path('missing'))
        self.assertIn(
            "FileNotFoundError while executing function 'file.read'", split_error(cm.exception)[2]
        )

    def testRm(self):
        for name in 'abc':
            self.write(name, name)
        self.run_insecure(
            '{file.rm(a)}{file.rm(bc)}', a=self.path('a'), bc=[self.path('b'), self.path('c')]
        )
        self.assertEqual(os.listdir(self.tmpdir), [])

    def testWrite(self):
        path = self.path('a')
        self.run_insecure(
            '{file.write(path, "first")}{file.write(path, list.new("second  ", "third"))}',
            path=path,
        )
        self.assertEqual(self.read('a'), 'first\nsecond\nthird\n')
        self.run_insecure('{file.write(path, lines, "w")}', path=path, lines=['new', 'lines'])
        self.assertEqual(self.read('a'), 'new\nlines\n')


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(fileTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
