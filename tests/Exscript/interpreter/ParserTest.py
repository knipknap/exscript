import contextlib
import io
import os
import tempfile
import unittest
from unittest import mock

from Exscript import stdlib
from Exscript.interpreter import Parser
from Exscript.interpreter.exception import PermissionError
from Exscript.interpreter.program import Program
from Exscript.interpreter.scope import Scope
from Exscript.parselib import Lexer
from Exscript.parselib.exception import CompileError, ExecuteError
from Exscript.util import template

from .helpers import split_error


class ParserTest(unittest.TestCase):
    """
    Compiling templates with the Parser.
    """

    CORRELATE = Parser

    def testConstructor(self):
        # Unlike Exscript.util.template, the parser allows all functions by default.
        parser = Parser()
        parser.define_object(**stdlib.functions)
        parser.parse('{sys.env("HOME")}')
        parser = Parser(secure=True)
        parser.define_object(**stdlib.functions)
        self.assertRaises(PermissionError, parser.parse, '{sys.env("HOME")}')
        parser.parse('{list.new()}')

        parser = Parser(no_prompt=True)
        self.assertRaises(CompileError, parser.parse, '{extract /(a)/ as a from "a"}')

    def testDefine(self):
        def function(scope):
            return [True]

        parser = Parser()
        parser.define(a='x', b=1, c=['y', 'z'], d=('t',), e=function)
        self.assertEqual(
            parser.variables, {'a': ['x'], 'b': [1], 'c': ['y', 'z'], 'd': ('t',), 'e': function}
        )
        variables = parser.parse('{x = a . b . c . e()}').execute()
        self.assertEqual(variables['x'], ['x1yTrue'])

    def testDefineObject(self):
        parser = Parser()
        parser.define_object(a='x', b=1)
        self.assertEqual(parser.variables, {'a': 'x', 'b': 1})

    def testParse(self):
        parser = Parser()
        parser.define(items=['a'])
        program = parser.parse('{x = items}{append "b" to x}', 'my.exscript')
        self.assertIsInstance(program, Program)
        self.assertEqual(program.execute()['x'], ['a', 'b'])
        self.assertEqual(parser.parse('{y = items}').execute()['y'], ['a'])
        self.assertEqual(parser.variables, {'items': ['a']})

        with self.assertRaises(CompileError) as cm:
            parser.parse('\n{x = }', 'my.exscript')
        message = "Expected term but got close_curly_bracket '}' in my.exscript:2"
        self.assertEqual(split_error(cm.exception), (['{x = }'], '     ^', message))

    def testParseFile(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        filename = os.path.join(tmpdir.name, 'test.exscript')
        with open(filename, 'w', encoding='utf-8') as fp:
            fp.write('{x = "Gr\u00fc\u00dfe"}\n{y = }\n')
        with self.assertRaises(CompileError) as cm:
            Parser().parse_file(filename)
        message = "Expected term but got close_curly_bracket '}' in %s:2" % filename
        self.assertEqual(split_error(cm.exception), (['{y = }'], '     ^', message))

        with open(filename, 'w', encoding='utf-8') as fp:
            fp.write('{x = "Gr\u00fc\u00dfe"}\n')
        variables = Parser().parse_file(filename).execute()
        self.assertEqual(variables['x'], ['Gr\u00fc\u00dfe'])


class ProgramTest(unittest.TestCase):
    """
    Running compiled templates.
    """

    def setUp(self):
        parser = Parser()
        parser.define(x='a')
        self.program = parser.parse('{y = x . "!"}')

    def testExecute(self):
        self.assertEqual(self.program.execute()['y'], ['a!'])
        variables = self.program.execute(variables={'x': ['b'], 'z': ['c']})
        self.assertEqual((variables['y'], variables['z']), (['b!'], ['c']))
        self.assertEqual(self.program.execute()['y'], ['a!'])

    def testInit(self):
        self.program.init(x='b', y=['ignored'], **{'f.g': 'ignored', '_h': 'ignored'})
        variables = self.program.execute()
        self.assertEqual(variables['y'], ['b!'])
        self.assertNotIn('f.g', variables)
        self.assertNotIn('_h', variables)
        self.program.init(x=['c', 'd'])
        self.assertEqual(self.program.execute()['y'], ['c!'])

    def testVariableThatIsUndefinedAtRuntime(self):
        with self.assertRaises(ExecuteError) as cm:
            self.program.execute(variables={'x': None})
        expected = (['{y = x . "!"}'], '     ^', "Undefined variable 'x' in None:1")
        self.assertEqual(split_error(cm.exception), expected)

    def testFunctionThatIsUndefinedAtRuntime(self):
        parser = Parser()
        parser.define_object(**stdlib.functions)
        program = parser.parse('{x = list.new()}')
        with self.assertRaises(ExecuteError) as cm:
            program.execute(variables={'list.new': None})
        expected = (
            ['{x = list.new()}'],
            '     ^^^^^^^^',
            "Undefined function 'list.new' in None:1",
        )
        self.assertEqual(split_error(cm.exception), expected)


class ScopeTest(unittest.TestCase):
    """
    The scopes that hold the variables; functions of the template language
    receive them as their first argument.
    """

    CORRELATE = Scope

    def setUp(self):
        lexer = Lexer(object)
        self.root = Scope('Root', lexer, None, variables={'a': [1]})
        self.child = Scope('Child', lexer, None, self.root)

    def testConstructor(self):
        lexer = Lexer(object)
        with self.assertRaises(TypeError) as cm:
            Scope('Root', lexer, None, variables={'x': 'a'})
        self.assertEqual(
            str(cm.exception), "Root: variable x must be a list, but got <class 'str'>"
        )
        Scope('Root', lexer, None, variables={'f.g': 'a', '_h': 1, 'i': []})

    def testDefine(self):
        self.child.define(b='x', c=['y'], **{'f.g': 'function', '_h': 'private'})
        self.assertEqual(
            self.root.variables,
            {'a': [1], 'b': ['x'], 'c': ['y'], 'f.g': 'function', '_h': 'private'},
        )
        self.assertEqual(self.child.variables, {})

    def testDefineObject(self):
        self.child.define_object(b='x')
        self.assertEqual(self.child.variables, {'b': 'x'})
        self.assertEqual(self.root.variables, {'a': [1]})

    def testGet(self):
        self.child.define_object(b='x')
        self.assertEqual(self.child.get('a'), [1])
        self.assertEqual(self.child.get('b'), 'x')
        self.assertIsNone(self.root.get('b'))
        self.assertEqual(self.root.get('b', 'default'), 'default')

    def testIsDefined(self):
        self.child.define_object(b='x')
        self.assertTrue(self.child.is_defined('a'))
        self.assertTrue(self.child.is_defined('b'))
        self.assertFalse(self.root.is_defined('b'))

    def testGetVars(self):
        self.child.define_object(a=[2], b='x')
        self.assertEqual(self.child.get_vars(), {'a': [2], 'b': 'x'})
        self.assertEqual(self.root.get_vars(), {'a': [1]})

    def testCopyPublicVars(self):
        self.child.define_object(b=['x'], _c='private')
        copied = self.child.copy_public_vars()
        self.assertEqual(copied, {'a': [1], 'b': ['x']})
        copied['b'].append('y')
        self.assertEqual(self.child.get('b'), ['x'])

    def testExitRequest(self):
        self.assertFalse(self.child.exit_requested)
        self.child.exit_request()
        self.assertTrue(self.child.exit_requested)

    def testValue(self):
        self.assertEqual(self.root.value(self.root), 1)
        program = Parser().parse('{x = 1}{y = "a"}')
        self.assertEqual(program.value(program), ['a'])

    def testDump(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.root.add(self.child)
            self.root.dump()
        self.assertEqual(out.getvalue(), 'Root start\n Child start\n Child end\nRoot end\n')

    def testDumpVars(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.child.dump_vars()
        self.assertEqual(out.getvalue(), "Scope: {'a': [1]}\n")


class CodeTest(unittest.TestCase):
    """
    Syntax errors in code blocks.
    """

    def assertCompileError(self, text, lines, marker, message):
        with self.assertRaises(CompileError) as cm:
            template.test(text)
        self.assertEqual(split_error(cm.exception), (lines, marker, message))

    def testUnexpectedToken(self):
        self.assertCompileError(
            '{x = 1 ,}', ['{x = 1 ,}'], '       ^', "Unexpected comma ',' in undefined:1"
        )
        self.assertCompileError('{as}', ['{as}'], ' ^^', "Unexpected keyword 'as' in undefined:1")

    def testUnterminatedCodeBlock(self):
        self.assertCompileError('{x = 1\n', [''], '^', "Unexpected EOF '' in undefined:2")

    def testComments(self):
        text = '{# a comment\n  x = 1\n# a comment\n  # another comment\n  y = 2 # not a comment\n}'
        with self.assertRaises(CompileError):
            Parser().parse(text)
        variables = Parser().parse(text.replace(' # not a comment', '')).execute()
        self.assertEqual((variables['x'], variables['y']), ([1], [2]))


class DumpTest(unittest.TestCase):
    """
    The dump of the parse tree, as with exscript --parser-verbose 5.
    """

    def dump(self, text, **kwargs):
        out = io.StringIO()
        with mock.patch.object(template, 'debug', 5), contextlib.redirect_stdout(out):
            template.test(text, **kwargs)
        return out.getvalue()

    def testDump(self):
        expected = (
            'Program start\n'
            ' Template start\n'
            "  Execute 'show $x'\n"
            '  Code start\n'
            '   Assign y start\n'
            '    Expression start\n'
            '     ExpressionNode + start\n'
            '      Term\n'
            '       Number 1\n'
            '      Operator +\n'
            '      ExpressionNode None start\n'
            '       Term\n'
            '        Variable x\n'
            '       Operator None\n'
            '      ExpressionNode None end\n'
            '     ExpressionNode + end\n'
            '    Expression end\n'
            '   Assign y end\n'
            '  Code end\n'
            ' Template end\n'
            'Program end\n'
        )
        self.assertEqual(self.dump('show $x\n{y = 1 + x}', x='1'), expected)

    def testDumpOfAllStatements(self):
        text = (
            '{\n'
            '  append "a" to l\n'
            '  if not 1 is 2\n'
            '    sys.message("yes")\n'
            '  else\n'
            '    fail "no" if 1 matches /1/i\n'
            '  end\n'
            '  loop l as i\n'
            '    enter\n'
            '  end\n'
            '  loop from 0 to 2 while 1\n'
            '  end\n'
            '  loop until 1\n'
            '  end\n'
            '  try\n'
            '  end\n'
            '  extract /(a)/ as a from l\n'
            '  if 0\n'
            '  end\n'
            '  fail "always"\n'
            '}\n'
            '<rpc><get/></rpc>\n'
        )
        dump = self.dump(text)
        for line in (
            'Append to l',
            'IfCondition start',
            'ExpressionNode not start',
            'FunctionCall sys.message start',
            'Fail start',
            "String 'always'",
            "Regex '1'",
            'Loop ',
            'While start',
            'Until start',
            'Enter',
            "Execute ''",
            'Try start',
            "Extract /(a)/ as a from ",
            "String 'yes'",
            'RPCBody start',
            "Execute '<get/>'",
        ):
            self.assertIn(line, dump)


def suite():
    loader = unittest.TestLoader()
    return unittest.TestSuite(
        [
            loader.loadTestsFromTestCase(ParserTest),
            loader.loadTestsFromTestCase(ProgramTest),
            loader.loadTestsFromTestCase(ScopeTest),
            loader.loadTestsFromTestCase(CodeTest),
            loader.loadTestsFromTestCase(DumpTest),
        ]
    )


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
