import sys
import unittest
import os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

import Exscript.util.syslog


class castTest(unittest.TestCase):
    CORRELATE = Exscript.util.syslog

    def testNetlog(self):
        from Exscript.util.syslog import netlog
        # NOTE: No idea how to test netlog.
        #  How to open a local syslog server? Mocking?


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(castTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
