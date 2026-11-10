import unittest

from Exscript.parselib.exception import CompileError, CompileWarning, ExecuteError

from .helpers import TemplateTestCase, split_error


class RpcTest(TemplateTestCase):
    """
    NETCONF RPCs in templates: the body of each <rpc> element is a command.
    """

    def testRpc(self):
        self.evaluate('<rpc>\n  <get>\n    <filter/>\n  </get>\n</rpc>\n')
        self.assertSent('<get>\n  <filter/>\n</get>')

    def testRpcOnOneLine(self):
        self.evaluate('<rpc><get-config><source><running/></source></get-config></rpc>\nls\n')
        self.assertSent('<get-config><source><running/></source></get-config>', 'ls')

    def testCommandBeforeAnRpc(self):
        self.evaluate('ls<rpc><get/></rpc>\n')
        self.assertSent('ls', '<get/>')

    def testRpcInABlock(self):
        self.evaluate('{if 1}<rpc><get/></rpc>{end}\n{if 0}<rpc><kill-session/></rpc>{end}\n')
        self.assertSent('<get/>')

    def testResponse(self):
        self.device.add_command('<get/>', '<data>abc</data>')
        variables = self.evaluate('<rpc><get/></rpc>{extract /<data>([^<]*)<\\/data>/ as data}\n')
        self.assertEqual(variables['data'], ['abc'])

    def testCommentsAreNotSent(self):
        self.evaluate('<rpc>\n  # a comment\n  <get>\n  # another comment\n  </get>\n</rpc>\n')
        self.assertSent('<get>\n</get>')

    def testHashBehindAnRpc(self):
        # Only lines starting with a hash, and the text behind a code block,
        # are comments.
        self.evaluate('<rpc><get/></rpc>  # not a comment\nls\n')
        self.assertSent('<get/>', '# not a comment', 'ls')

    def testVariables(self):
        text = '<rpc><get-config><source><$source/></source></get-config></rpc>\n'
        self.evaluate(text, source='candidate')
        self.assertSent('<get-config><source><candidate/></source></get-config>')

    def testEmptyRpc(self):
        self.evaluate('<rpc></rpc>\n<rpc>\n</rpc>\n')
        self.assertSent()

    def testUndefinedVariable(self):
        with self.assertRaises(ExecuteError) as cm:
            self.evaluate('<rpc>\n  <get>$nothing</get>\n</rpc>\n')
        message = "Undefined variable 'nothing' in undefined:2"
        self.assertError(cm.exception, ['  <get>$nothing</get>'], '       ^^^^^^^^', message)

    def testInvalidXml(self):
        with self.assertRaises(CompileError) as cm:
            self.evaluate('ls\n<rpc>\n  <get>\n</rpc>\n')
        lines, marker, message = split_error(cm.exception)
        self.assertEqual((lines, marker), (['</rpc>'], '      ^'))
        self.assertTrue(
            message.startswith(
                'XML validation of the RPC command has failed. The error was caused by:\n'
                'XMLSyntaxError: '
            ),
            message,
        )
        self.assertTrue(message.endswith(' in undefined:4'), message)
        self.assertSent()

    def testInvalidXmlWithVariables(self):
        # The values of the variables might make the XML valid.
        with self.assertWarns(CompileWarning) as cm:
            self.evaluate('<rpc>\n  <$tag>\n</rpc>\n', tag='get/')
        lines, marker, message = split_error(cm.warning)
        self.assertEqual((lines, marker), (['</rpc>'], '      ^'))
        self.assertIn('This could be a real syntax error or might depend on the final', message)
        self.assertSent('<get/>')

    def testCharacterThatIsNotUtf8(self):
        with self.assertRaises(CompileError) as cm:
            self.evaluate('<rpc>\n  <get>\ud800</get>\n</rpc>\n')
        lines, marker, message = split_error(cm.exception)
        self.assertEqual((lines, marker), (['  <get>\ud800</get>'], '       ^'))
        self.assertIn('UnicodeEncodeError', message)

    def testSyntaxErrors(self):
        for text, lines, marker, message in (
            ('<rpc>\n  <get/>\n', [''], '^', "Expected '</rpc>' but got EOF in undefined:3"),
            (
                '<rpc><rpc></rpc>\n',
                ['<rpc><rpc></rpc>'],
                '     ^^^^^',
                "Unexpected open_rpc_tag '<rpc>' in undefined:1",
            ),
            ('</rpc>\n', ['</rpc>'], '^^^^^^', "Unexpected close_rpc_tag '</rpc>' in undefined:1"),
        ):
            with self.subTest(text=text):
                with self.assertRaises(CompileError) as cm:
                    self.evaluate(text)
                self.assertError(cm.exception, lines, marker, message)


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(RpcTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
