import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

import Exscript.util.ipv6

class ipv6Test(unittest.TestCase):
    CORRELATE = Exscript.util.ipv6

    def testIsIp(self):
        from Exscript.util.ipv6 import is_ip
        self.assert_(is_ip('::'))
        self.assert_(is_ip('1::'))
        self.assert_(is_ip('::A'))
        self.assert_(is_ip('1234::2222'))
        self.assert_(is_ip('1234:0:01:02::'))
        self.assert_(is_ip('1:2:3:4:5:6:7:8'))
        self.failIf(is_ip(':::'))
        self.failIf(is_ip('1:2:3:4:5:6:7:8:9'))
        self.failIf(is_ip('1::A::2'))
        self.failIf(is_ip('1::A::'))
        self.failIf(is_ip('::A::'))
        self.failIf(is_ip('::A::1'))
        self.failIf(is_ip('A'))
        self.failIf(is_ip('X::'))

    def testNormalizeIp(self):
        from Exscript.util.ipv6 import normalize_ip
        self.assertEqual(normalize_ip('::'),
                         '0000:0000:0000:0000:0000:0000:0000:0000')
        self.assertEqual(normalize_ip('1::'),
                         '0001:0000:0000:0000:0000:0000:0000:0000')
        self.assertEqual(normalize_ip('::A'),
                         '0000:0000:0000:0000:0000:0000:0000:000a')
        self.assertEqual(normalize_ip('1234::2222'),
                         '1234:0000:0000:0000:0000:0000:0000:2222')
        self.assertEqual(normalize_ip('1234:0:01:02::'),
                         '1234:0000:0001:0002:0000:0000:0000:0000')

    def testCleanIp(self):
        from Exscript.util.ipv6 import clean_ip

        self.assertEqual(clean_ip('1234:0:0:0:0:0:0:000A'), '1234::a')
        self.assertEqual(clean_ip('1234:0:0:0:1:0:0:0'), '1234:0:0:0:1::')
        self.assertEqual(clean_ip('0:0:0:0:0:0:0:0'), '::')
        self.assertEqual(clean_ip('0001:0:0:0:0000:0000:0000:0000'), '1::')
        self.assertEqual(clean_ip('::A'), '::a')
        self.assertEqual(clean_ip('A::A'), 'a::a')
        self.assertEqual(clean_ip('A::'), 'a::')
        self.assertEqual(clean_ip('1234:0:01:02::'), '1234:0:1:2::')

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(ipv6Test)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
