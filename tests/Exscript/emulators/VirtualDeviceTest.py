from __future__ import unicode_literals
import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from Exscript.emulators import VirtualDevice

class VirtualDeviceTest(unittest.TestCase):
    CORRELATE    = VirtualDevice
    cls          = VirtualDevice
    banner       = 'Welcome to myhost!\n'
    prompt       = 'myhost> '
    userprompt   = 'User: '
    passwdprompt = 'Password: '

    def testConstructor(self):
        self.cls('myhost')

    def testGetPrompt(self):
        v = self.cls('myhost')
        self.assertEqual(v.get_prompt(), self.prompt)
        v.set_prompt('foo# ')
        self.assertEqual(v.get_prompt(), 'foo# ')

    def testSetPrompt(self):
        self.testGetPrompt()

    def testAddCommand(self):
        cs = self.cls('myhost',
                      strict     = True,
                      echo       = False,
                      login_type = self.cls.LOGIN_TYPE_NONE)
        self.assertRaises(Exception, cs.do, 'foo')
        cs.add_command('foo', 'bar')
        self.assertEqual(cs.do('foo'), 'bar\n' + self.prompt)

        def sayhello(cmd):
            return 'hello'
        cs.add_command('hi$', sayhello)
        self.assertEqual(cs.do('hi'), 'hello\n' + self.prompt)
        cs.add_command('hi2$', sayhello, prompt = False)
        self.assertEqual(cs.do('hi2'), 'hello')

    def testAddCommandsFromFile(self):
        pass # FIXME

    def testInit(self):
        cs = self.cls('myhost',
                      login_type = self.cls.LOGIN_TYPE_PASSWORDONLY)
        self.assertEqual(cs.init(), self.banner + self.passwdprompt)

        cs = self.cls('myhost',
                      login_type = self.cls.LOGIN_TYPE_USERONLY)
        self.assertEqual(cs.init(), self.banner + self.userprompt)

        cs = self.cls('myhost',
                      login_type = self.cls.LOGIN_TYPE_BOTH)
        self.assertEqual(cs.init(), self.banner + self.userprompt)

        cs = self.cls('myhost',
                      login_type = self.cls.LOGIN_TYPE_NONE)
        self.assertEqual(cs.init(), self.banner + self.prompt)

    def testDo(self):
        pass # See testAddCommand()

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(VirtualDeviceTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
