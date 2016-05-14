from __future__ import unicode_literals
import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

import Exscript.util.crypt

class cryptTest(unittest.TestCase):
    CORRELATE = Exscript.util.crypt

    def testOtp(self):
        from Exscript.util.crypt import otp
        hash = otp('password', 'abc123', 9999)
        self.assertEqual('ACTA AMMO CAR WEB BIN YAP', hash)
        hash = otp('password', 'abc123', 9998)
        self.assertEqual('LESS CLUE LISA MEAT MAGI USER', hash)
        hash = otp('pass', 'abc123', 9998)
        self.assertEqual('DRAB LEER VOTE RICH NEWS FRAU', hash)
        hash = otp('pass', 'abc888', 9998)
        self.assertEqual('DEBT BOON ASKS ORAL MEN WEE', hash)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(cryptTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
