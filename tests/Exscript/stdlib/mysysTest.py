import contextlib
import io
import os
import shlex
import subprocess
import sys
import unittest
from unittest import mock

from interpreter.helpers import TemplateTestCase

import Exscript.stdlib.mysys


def command_line(*args):
    """
    Returns a command line that runs Python with the given arguments, quoted
    for sys.exec() on this platform.
    """
    if os.name == 'nt':
        return subprocess.list2cmdline([sys.executable, *args])
    return shlex.join([sys.executable, *args])


class mysysTest(TemplateTestCase):
    """
    The system functions of the template language, sys.*.
    """

    CORRELATE = Exscript.stdlib.mysys

    def testEnv(self):
        with mock.patch.dict(os.environ, {'EXSCRIPT_TEST_VALUE': 'a value'}):
            os.environ.pop('EXSCRIPT_TEST_UNSET', None)
            text = '{a = sys.env("EXSCRIPT_TEST_VALUE")}{b = sys.env("EXSCRIPT_TEST_UNSET")}'
            variables = self.evaluate(text, secure=False)
        self.assertEqual((variables['a'], variables['b']), (['a value'], ['']))

    def testExecute(self):
        code = 'import sys; print("out", flush=True); print("err", file=sys.stderr, flush=True)'
        variables = self.evaluate(
            '{sys.exec(command)}', command=command_line('-c', code), secure=False
        )
        self.assertEqual(variables['__response__'], ['out\n', 'err\n'])
        self.assertSent()

    def testExecuteWithoutInput(self):
        code = 'import sys; print(repr(sys.stdin.read()))'
        variables = self.evaluate(
            '{sys.exec(command)}', command=command_line('-c', code), secure=False
        )
        self.assertEqual(variables['__response__'], ["''\n"])

    def testMessage(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.evaluate('{sys.message("hello $__hostname__")}{sys.message(list.new("a", "b"))}')
        self.assertEqual(out.getvalue(), 'hello r1\nab\n')

    def testWait(self):
        with mock.patch.object(Exscript.stdlib.mysys.time, 'sleep') as sleep:
            self.evaluate('{sys.wait(2)}{sys.wait("3")}')
        self.assertEqual(sleep.call_args_list, [mock.call(2), mock.call(3)])


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(mysysTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
