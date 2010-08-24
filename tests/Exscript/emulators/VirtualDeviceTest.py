import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from Exscript.emulators import VirtualDevice

class VirtualDeviceTest(unittest.TestCase):
    CORRELATE = VirtualDevice

    def testConstructor(self):
        VirtualDevice('myhost')

    def testGetPrompt(self):
        v = VirtualDevice('myhost')
        self.assertEqual(v.get_prompt(), 'myhost> ')
        v.set_prompt('foo# ')
        self.assertEqual(v.get_prompt(), 'foo# ')

    def testSetPrompt(self):
        self.testGetPrompt()

    def testAddCommand(self):
        cs = VirtualDevice('myhost',
                           strict     = True,
                           echo       = False,
                           login_type = VirtualDevice.LOGIN_TYPE_NONE)
        self.assertRaises(Exception, cs.do, 'foo')
        cs.add_command('foo', 'bar')
        self.assertEqual(cs.do('foo'), 'bar\nmyhost> ')

        def sayhello(cmd):
            return 'hello'
        cs.add_command('hi$', sayhello)
        self.assertEqual(cs.do('hi'), 'hello\nmyhost> ')
        cs.add_command('hi2$', sayhello, prompt = False)
        self.assertEqual(cs.do('hi2'), 'hello')

    def testAddCommandsFromFile(self):
        pass # FIXME

    def testInit(self):
        cs = VirtualDevice('testhost',
                           login_type = VirtualDevice.LOGIN_TYPE_PASSWORDONLY)
        self.assertEqual(cs.init(), 'Welcome to testhost!\nPassword: ')

        cs = VirtualDevice('testhost',
                           login_type = VirtualDevice.LOGIN_TYPE_USERONLY)
        self.assertEqual(cs.init(), 'Welcome to testhost!\nUsername: ')

        cs = VirtualDevice('testhost',
                           login_type = VirtualDevice.LOGIN_TYPE_BOTH)
        self.assertEqual(cs.init(), 'Welcome to testhost!\nUsername: ')

        cs = VirtualDevice('testhost',
                           login_type = VirtualDevice.LOGIN_TYPE_NONE)
        self.assertEqual(cs.init(), 'Welcome to testhost!\ntesthost> ')

    def testDo(self):
        pass # See testAddCommand()

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(VirtualDeviceTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
