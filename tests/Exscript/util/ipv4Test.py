import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

import Exscript.util.ipv4

class ipv4Test(unittest.TestCase):
    CORRELATE = Exscript.util.ipv4

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(ipv4Test)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
