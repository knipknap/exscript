import copy
import os
import tempfile
import unittest

from Exscript.emulators import CommandSet


class CommandSetTest(unittest.TestCase):
    CORRELATE = CommandSet

    def testConstructor(self):
        CommandSet()
        CommandSet(strict=True)
        CommandSet(strict=False)

    def testAdd(self):
        cs = CommandSet()
        self.assertRaises(Exception, cs.eval, 'foo')

        cs = CommandSet(strict=False)
        self.assertEqual(cs.eval('foo'), None)

        cs = CommandSet(strict=True)
        self.assertRaises(Exception, cs.eval, 'foo')
        cs.add('foo', 'bar')
        self.assertEqual(cs.eval('foo'), 'bar')

        def sayhello(cmd):
            return 'hello'

        cs.add('hi', sayhello)
        self.assertEqual(cs.eval('hi'), 'hello')

    def writeFile(self, source):
        tmpdir = self.enterContext(tempfile.TemporaryDirectory())
        filename = os.path.join(tmpdir, 'commands.py')
        with open(filename, 'w', encoding='utf-8') as fp:
            fp.write(source)
        return filename

    def testAddFromFile(self):
        # A response of None marks a command without a response, also in strict mode.
        filename = self.writeFile(
            'def uptime(command):\n'
            '    return "up 2 days"\n'
            'commands = [("show uptime", uptime), (r"show ver.*", "IOS 15.2"), ("clear", None)]\n'
        )
        cs = CommandSet(strict=True)
        cs.add_from_file(filename)
        self.assertEqual(cs.eval('show uptime'), 'up 2 days')
        self.assertEqual(cs.eval('show version'), 'IOS 15.2')
        self.assertIsNone(cs.eval('clear'))
        self.assertRaises(ValueError, cs.eval, 'reload')

    def testAddFromFileWithoutCommands(self):
        cs = CommandSet()
        for source, error in (
            ('responses = []\n', 'no variable named "commands"'),
            ('commands = 42\n', 'variable "commands" is not iterable'),
        ):
            with self.subTest(source=source):
                filename = self.writeFile(source)
                with self.assertRaisesRegex(ValueError, error):
                    cs.add_from_file(filename)

    def testEval(self):
        pass  # See testAdd()

    def testDeepcopy(self):
        cs = CommandSet(strict=False)
        cs.add('show version', 'IOS 15.2')
        clone = copy.deepcopy(cs)
        self.assertFalse(clone.strict)
        self.assertEqual(clone.eval('show version'), 'IOS 15.2')
        clone.add('show uptime', 'up 2 days')
        self.assertEqual(clone.eval('show uptime'), 'up 2 days')
        self.assertIsNone(cs.eval('show uptime'))  # the original is unchanged


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(CommandSetTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
