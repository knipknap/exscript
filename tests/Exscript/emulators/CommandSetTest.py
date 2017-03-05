import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from Exscript.emulators import CommandSet

class CommandSetTest(unittest.TestCase):
    CORRELATE = CommandSet

    def testConstructor(self):
        CommandSet()
        CommandSet(strict = True)
        CommandSet(strict = False)

    def testAdd(self):
        cs = CommandSet()
        self.assertRaises(Exception, cs.eval, 'foo')

        cs = CommandSet(strict = False)
        self.assertEqual(cs.eval('foo'), None)

        cs = CommandSet(strict = True)
        self.assertRaises(Exception, cs.eval, 'foo')
        cs.add('foo', 'bar')
        self.assertEqual(cs.eval('foo'), 'bar')

        def sayhello(cmd):
            return 'hello'
        cs.add('hi', sayhello)
        self.assertEqual(cs.eval('hi'), 'hello')

    def testAddFromFile(self):
        pass # FIXME

    def testEval(self):
        pass # See testAdd()

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(CommandSetTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
