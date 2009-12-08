import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

import Exscript.util.file

class fileTest(unittest.TestCase):
    CORRELATE = Exscript.util.file

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(fileTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
