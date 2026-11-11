import os
import tempfile
import unittest

from hypothesis import given, settings
from hypothesis import strategies as st
from interpreter.helpers import RecordingDevice, connect, split_error

from Exscript import stdlib
from Exscript.interpreter.exception import PermissionError
from Exscript.parselib.exception import CompileError
from Exscript.util import template

# The functions that run local commands or access local files.
INSECURE = {
    'file.chmod',
    'file.clear',
    'file.mkdir',
    'file.read',
    'file.rm',
    'file.write',
    'sys.env',
    'sys.exec',
}

# Statements with a function call (%s), also where the call never runs.
CALLS = (
    '{%s}',
    '{x = %s}',
    '{if 0}{%s}{end}',
    '{if %s}{end}',
    '{loop from 0 to 0}{%s}{end}',
    '{loop %s as item}{end}',
    '{loop while %s}{end}',
    '{fail "x" if %s}',
    '{x = string.toupper(%s)}',
    '{try}{%s}{end}',
    '{append %s to y}',
    '{extract /(a)/ as z from %s}',
    'ls\n{%s}',
)

statements = st.tuples(st.sampled_from(sorted(stdlib.functions)), st.sampled_from(CALLS))


def shout(scope, string):
    """A function that the caller passes to the template."""
    return [string[0].upper()]


class templateTest(unittest.TestCase):
    CORRELATE = template

    def setUp(self):
        self.device = RecordingDevice()
        self.device.add_command('ls', 'file1\nfile2')
        self.conn = connect(self.device)
        self.addCleanup(self.conn.close, force=True)
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        self.tmpdir = tmpdir.name

    def write(self, text):
        """
        Writes the given template to a file and returns its name.
        """
        filename = os.path.join(self.tmpdir, 'test.exscript')
        with open(filename, 'w', encoding='utf-8') as fp:
            fp.write(text)
        return filename

    def testTest(self):
        self.assertIsNone(template.test('ls\n{x = y}', y='a'))
        self.assertRaises(NameError, template.test, '{x = y}')
        with self.assertRaises(CompileError) as cm:
            template.test('ls\n{x = }')
        message = "Expected term but got close_curly_bracket '}' in undefined:2"
        self.assertEqual(split_error(cm.exception), (['{x = }'], '     ^', message))
        self.assertEqual(self.device.received, [])

    def testTestFile(self):
        filename = self.write('ls\n{x = y . "\u00e9"}\n')
        self.assertIsNone(template.test_file(filename, y='a'))
        filename = self.write('ls\n{x = }\n')
        with self.assertRaises(CompileError) as cm:
            template.test_file(filename)
        self.assertTrue(str(cm.exception).endswith(' in %s:2' % filename))
        self.assertEqual(self.device.received, [])

    def testEval(self):
        variables = template.eval(
            self.conn, 'ls\n{x = y}\n{u = __username__}{f = __filename__}', y='a'
        )
        self.assertEqual(self.device.received, ['ls\r'])
        self.assertEqual(variables['__response__'], ['file1', 'file2'])
        self.assertEqual(variables['__hostname__'], ['r1'])
        self.assertEqual(
            (variables['x'], variables['u'], variables['f']), (['a'], ['undefined'], ['undefined'])
        )
        self.assertIs(variables['__connection__'], self.conn)

    def testEvalWithOptions(self):
        variables = template.eval(self.conn, 'ls\n', strip_command=False)
        self.assertEqual(variables['__response__'], ['ls', 'file1', 'file2'])
        template.eval(self.conn, 'ls \\x41\n', no_escaping=True)
        self.assertEqual(self.device.received, ['ls\r', 'ls x41\r'])

    def testEvalBuiltinVariables(self):
        # The caller may override the built-in variables.
        variables = template.eval(self.conn, '{h = __hostname__}', __hostname__='other')
        self.assertEqual((variables['h'], variables['__hostname__']), (['other'], ['other']))

    def testEvalFile(self):
        filename = self.write('ls\n{f = __filename__}\n')
        variables = template.eval_file(self.conn, filename)
        self.assertEqual(self.device.received, ['ls\r'])
        self.assertEqual(variables['f'], [filename])
        variables = template.eval_file(self.conn, filename, strip_command=False)
        self.assertEqual(variables['__response__'], ['ls', 'file1', 'file2'])

    def testPaste(self):
        variables = template.paste(self.conn, 'ls\n{x = y}\nls \\x41\n', y='a')
        self.assertEqual(self.device.received, ['ls\r', 'ls A\r'])
        self.assertEqual((variables['__response__'], variables['x']), ([''], ['a']))
        template.paste(self.conn, 'ls \\x41\n', no_escaping=True)
        self.assertEqual(self.device.received[2:], ['ls x41\r'])

    def testPasteFile(self):
        filename = self.write('ls\n{f = __filename__}\n')
        variables = template.paste_file(self.conn, filename)
        self.assertEqual(self.device.received, ['ls\r'])
        self.assertEqual((variables['__response__'], variables['f']), ([''], [filename]))

    def testSecureModeIsTheDefault(self):
        for source in '{sys.exec("true")}', '{sys.env("HOME")}', '{file.rm("x")}':
            self.assertRaises(PermissionError, template.test, source)
            self.assertRaises(PermissionError, template.eval, self.conn, source)
            self.assertRaises(PermissionError, template.paste, self.conn, source)
            template.test(source, secure=False)

    def testInsecureFunctionsAreForbidden(self):
        for name in sorted(INSECURE):
            text = 'ls\n{%s()}\n' % name
            filename = self.write(text)
            for function, args in (
                (template.test, (text,)),
                (template.eval, (self.conn, text)),
                (template.paste, (self.conn, text)),
                (template.test_file, (filename,)),
                (template.eval_file, (self.conn, filename)),
                (template.paste_file, (self.conn, filename)),
            ):
                with self.subTest(name=name, function=function.__name__):
                    with self.assertRaises(PermissionError) as cm:
                        function(*args)
                    lines, marker, message = split_error(cm.exception)
                    self.assertEqual((lines, marker), (['{%s()}' % name], ' ' + '^' * len(name)))
                    origin = filename if function.__name__.endswith('_file') else 'undefined'
                    expected = 'Use of insecure function %r is not permitted in %s:2' % (
                        name,
                        origin,
                    )
                    self.assertEqual(message, expected)
        self.assertEqual(self.device.received, [])

    def testInsecureFunctionsAreForbiddenEverywhere(self):
        for call in CALLS:
            text = call % 'file.read("x")'
            with self.subTest(text=text):
                self.assertRaises(PermissionError, template.test, text)
                template.test(text, secure=False)

    def testSecureFunctionsAreAllowed(self):
        template.test('{sys.message("hello")}{file.exists("x")}')
        for name in sorted(set(stdlib.functions) - INSECURE):
            with self.subTest(name=name):
                template.test('{%s()}' % name)

    @settings(max_examples=100, deadline=None)
    @given(st.lists(statements, min_size=1, max_size=4))
    def testOnlySecureFunctionsInSecureMode(self, calls):
        text = '\n'.join(call % (name + '()') for name, call in calls) + '\n'
        template.test(text, secure=False)
        insecure = [name for name, _ in calls if name in INSECURE]
        if not insecure:
            template.test(text)
            return
        with self.assertRaises(PermissionError) as cm:
            template.test(text)
        self.assertIn(
            'Use of insecure function %r is not permitted' % insecure[0], str(cm.exception)
        )

    def testFunctionsOfTheCallerAreAllowed(self):
        variables = template.eval(self.conn, '{x = shout("hi")}', shout=shout)
        self.assertEqual(variables['x'], ['HI'])

    @unittest.skipIf(os.name == 'nt', 'echo is a shell builtin on Windows')
    def testExecDoesNotUseAShell(self):
        variables = template.eval(self.conn, '{sys.exec("echo a;echo b")}', secure=False)
        self.assertEqual(variables['__response__'], ['a;echo b\n'])


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(templateTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
