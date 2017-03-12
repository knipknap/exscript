import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

import Exscript.util.syslog

class castTest(unittest.TestCase):
    CORRELATE = Exscript.util.syslog

    def testNetlog(self):
        from Exscript.util.syslog import netlog
        #FIXME: dont really know how to test this; we'd need to know
        # how to open a local syslog server.

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(castTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
