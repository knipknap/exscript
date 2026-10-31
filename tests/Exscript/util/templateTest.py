import os
import unittest

from Exscript.emulators import VirtualDevice
from Exscript.interpreter.exception import PermissionError
from Exscript.protocols import Dummy
from Exscript.util import template


def shout(scope, string):
    """A function that the caller passes to the template."""
    return [string[0].upper()]


class templateTest(unittest.TestCase):
    CORRELATE = template

    def setUp(self):
        self.conn = Dummy(device=VirtualDevice('r1', strict=False), connect_rate_limit=0)
        self.conn.connect('r1')
        self.addCleanup(self.conn.close, force=True)

    def testSecureModeIsTheDefault(self):
        for source in '{sys.exec("true")}', '{sys.env("HOME")}', '{file.rm("x")}':
            self.assertRaises(PermissionError, template.test, source)
            self.assertRaises(PermissionError, template.eval, self.conn, source)
            self.assertRaises(PermissionError, template.paste, self.conn, source)
            template.test(source, secure=False)

    def testSecureFunctionsAreAllowed(self):
        template.test('{sys.message("hello")}{file.exists("x")}')

    def testFunctionsOfTheCallerAreAllowed(self):
        variables = template.eval(self.conn, '{x = shout("hi")}', shout=shout)
        self.assertEqual(variables['x'], ['HI'])

    @unittest.skipIf(os.name == 'nt', 'echo is a shell builtin on Windows')
    def testExecDoesNotUseAShell(self):
        variables = template.eval(self.conn, '{sys.exec("echo a;echo b")}', secure=False)
        self.assertEqual(variables['__response__'], ['a;echo b\n'])
