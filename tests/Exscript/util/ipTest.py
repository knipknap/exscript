import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

import Exscript.util.ip

class ipTest(unittest.TestCase):
    CORRELATE = Exscript.util.ip

    def testIsIp(self):
        from Exscript.util.ip import is_ip
        self.assert_(is_ip('0.0.0.0'))
        self.assert_(is_ip('::'))
        self.assert_(not is_ip('1'))

    def testNormalizeIp(self):
        from Exscript.util.ip import normalize_ip
        self.assertEqual(normalize_ip('0.128.255.0'), '000.128.255.000')
        self.assertEqual(normalize_ip('1234:0:01:02::'),
                         '1234:0000:0001:0002:0000:0000:0000:0000')

    def testCleanIp(self):
        from Exscript.util.ip import clean_ip
        self.assertEqual(clean_ip('192.168.010.001'), '192.168.10.1')
        self.assertEqual(clean_ip('1234:0:0:0:0:0:0:000A'), '1234::a')

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(ipTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
