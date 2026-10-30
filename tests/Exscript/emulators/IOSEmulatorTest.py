import unittest


from Exscript.emulators import IOSEmulator
from Exscript.emulators.iosemu import iosbanner

from .VirtualDeviceTest import VirtualDeviceTest


class IOSEmulatorTest(VirtualDeviceTest):
    CORRELATE = IOSEmulator
    cls = IOSEmulator
    banner = iosbanner % ('myhost', 'myhost', 'myhost')
    prompt = 'myhost#'
    userprompt = 'Username: '
    passwdprompt = 'Password: '

    def testAddCommand(self):
        VirtualDeviceTest.testAddCommand(self)

        cs = self.cls('myhost',
                      strict=True,
                      echo=False,
                      login_type=self.cls.LOGIN_TYPE_NONE)

        response = cs.do('show version')
        self.assertTrue(response.startswith(
            '\nCisco Internetwork Operating'), response)


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(IOSEmulatorTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
