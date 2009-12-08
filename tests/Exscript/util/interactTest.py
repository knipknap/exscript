import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

import Exscript.util.interact

class interactTest(unittest.TestCase):
    CORRELATE = Exscript.util.interact

    def testGetUser(self):
        from Exscript.util.interact import get_user
        # Can't really be tested, as it is interactive.

    def testGetLogin(self):
        from Exscript.util.interact import get_login
        # Can't really be tested, as it is interactive.

    def testReadLogin(self):
        from Exscript.util.interact import read_login
        # Can't really be tested, as it is interactive.

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(interactTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
