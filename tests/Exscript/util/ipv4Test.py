from builtins import range
import sys
import unittest
import re
import os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

import Exscript.util.ipv4


class ipv4Test(unittest.TestCase):
    CORRELATE = Exscript.util.ipv4

    def testIsIp(self):
        from Exscript.util.ipv4 import is_ip
        self.assertTrue(is_ip('0.0.0.0'))
        self.assertTrue(is_ip('255.255.255.255'))
        self.assertTrue(is_ip('1.2.3.4'))
        self.assertTrue(not is_ip(''))
        self.assertTrue(not is_ip('1'))
        self.assertTrue(not is_ip('1.2.3.'))
        self.assertTrue(not is_ip('.1.2.3'))
        self.assertTrue(not is_ip('1.23.4'))
        self.assertTrue(not is_ip('1..3.4'))

    def testNormalizeIp(self):
        from Exscript.util.ipv4 import normalize_ip
        self.assertEqual(normalize_ip('0.0.0.0'),         '000.000.000.000')
        self.assertEqual(normalize_ip('255.255.255.255'), '255.255.255.255')
        self.assertEqual(normalize_ip('001.002.003.004'), '001.002.003.004')
        self.assertEqual(normalize_ip('192.168.010.001'), '192.168.010.001')
        self.assertEqual(normalize_ip('0.128.255.0'),     '000.128.255.000')

    def testCleanIp(self):
        from Exscript.util.ipv4 import clean_ip
        self.assertEqual(clean_ip('0.0.0.0'),         '0.0.0.0')
        self.assertEqual(clean_ip('255.255.255.255'), '255.255.255.255')
        self.assertEqual(clean_ip('001.002.003.004'), '1.2.3.4')
        self.assertEqual(clean_ip('192.168.010.001'), '192.168.10.1')
        self.assertEqual(clean_ip('0.128.255.0'),     '0.128.255.0')

    def testIp2Int(self):
        from Exscript.util.ipv4 import ip2int
        self.assertEqual(ip2int('0.0.0.0'),         0x00000000)
        self.assertEqual(ip2int('255.255.255.255'), 0xFFFFFFFF)
        self.assertEqual(ip2int('255.255.255.0'),   0xFFFFFF00)
        self.assertEqual(ip2int('0.255.255.0'),     0x00FFFF00)
        self.assertEqual(ip2int('0.128.255.0'),     0x0080FF00)

    def testInt2Ip(self):
        from Exscript.util.ipv4 import int2ip, ip2int
        for ip in ('0.0.0.0',
                   '255.255.255.255',
                   '255.255.255.0',
                   '0.255.255.0',
                   '0.128.255.0'):
            self.assertEqual(int2ip(ip2int(ip)), ip)

    def testPfxlen2MaskInt(self):
        from Exscript.util.ipv4 import pfxlen2mask_int, int2ip
        self.assertEqual(int2ip(pfxlen2mask_int(32)), '255.255.255.255')
        self.assertEqual(int2ip(pfxlen2mask_int(31)), '255.255.255.254')
        self.assertEqual(int2ip(pfxlen2mask_int(30)), '255.255.255.252')
        self.assertEqual(int2ip(pfxlen2mask_int(2)),  '192.0.0.0')
        self.assertEqual(int2ip(pfxlen2mask_int(1)),  '128.0.0.0')
        self.assertEqual(int2ip(pfxlen2mask_int(0)),  '0.0.0.0')

    def testPfxlen2Mask(self):
        from Exscript.util.ipv4 import pfxlen2mask
        self.assertEqual(pfxlen2mask(32), '255.255.255.255')
        self.assertEqual(pfxlen2mask(31), '255.255.255.254')
        self.assertEqual(pfxlen2mask(30), '255.255.255.252')
        self.assertEqual(pfxlen2mask(2),  '192.0.0.0')
        self.assertEqual(pfxlen2mask(1),  '128.0.0.0')
        self.assertEqual(pfxlen2mask(0),  '0.0.0.0')

    def testMask2Pfxlen(self):
        from Exscript.util.ipv4 import mask2pfxlen
        self.assertEqual(32, mask2pfxlen('255.255.255.255'))
        self.assertEqual(31, mask2pfxlen('255.255.255.254'))
        self.assertEqual(30, mask2pfxlen('255.255.255.252'))
        self.assertEqual(2,  mask2pfxlen('192.0.0.0'))
        self.assertEqual(1,  mask2pfxlen('128.0.0.0'))
        self.assertEqual(0,  mask2pfxlen('0.0.0.0'))

    def testParsePrefix(self):
        from Exscript.util.ipv4 import parse_prefix
        self.assertEqual(('1.2.3.4', 24), parse_prefix('1.2.3.4'))
        self.assertEqual(('1.2.3.4', 32), parse_prefix('1.2.3.4',    32))
        self.assertEqual(('1.2.3.4', 15), parse_prefix('1.2.3.4/15'))
        self.assertEqual(('1.2.3.4', 15), parse_prefix('1.2.3.4/15', 32))

    def testNetwork(self):
        from Exscript.util.ipv4 import network
        self.assertEqual(network('10.0.0.0/30'), '10.0.0.0')
        self.assertEqual(network('10.0.0.1/30'), '10.0.0.0')
        self.assertEqual(network('10.0.0.2/30'), '10.0.0.0')
        self.assertEqual(network('10.0.0.3/30'), '10.0.0.0')
        self.assertEqual(network('10.0.0.0/24'), '10.0.0.0')
        self.assertEqual(network('10.0.0.255/24'), '10.0.0.0')

    def testBroadcast(self):
        from Exscript.util.ipv4 import broadcast
        self.assertEqual(broadcast('10.0.0.0/30'), '10.0.0.3')
        self.assertEqual(broadcast('10.0.0.1/30'), '10.0.0.3')
        self.assertEqual(broadcast('10.0.0.2/30'), '10.0.0.3')
        self.assertEqual(broadcast('10.0.0.3/30'), '10.0.0.3')
        self.assertEqual(broadcast('10.0.0.0/24'), '10.0.0.255')
        self.assertEqual(broadcast('10.0.0.255/24'), '10.0.0.255')

    def testRemoteIp(self):
        from Exscript.util.ipv4 import remote_ip
        self.assertEqual(remote_ip('10.0.0.0'), '10.0.0.3')
        self.assertEqual(remote_ip('10.0.0.1'), '10.0.0.2')
        self.assertEqual(remote_ip('10.0.0.2'), '10.0.0.1')
        self.assertEqual(remote_ip('10.0.0.3'), '10.0.0.0')

    def testMatchesPrefix(self):
        from Exscript.util.ipv4 import matches_prefix
        self.assertTrue(matches_prefix('10.0.0.0', '10.0.0.0/8'))
        self.assertTrue(matches_prefix('10.255.255.255', '10.0.0.0/8'))
        self.assertFalse(matches_prefix('11.0.0.0', '10.0.0.0/8'))
        self.assertFalse(matches_prefix('9.255.255.255', '10.0.0.0/8'))

    def testIsPrivate(self):
        from Exscript.util.ipv4 import is_private
        self.assertFalse(is_private('9.255.255.255'))
        self.assertTrue(is_private('10.0.0.0'))
        self.assertTrue(is_private('10.255.255.255'))
        self.assertFalse(is_private('11.0.0.0'))

        self.assertFalse(is_private('172.15.255.255'))
        self.assertTrue(is_private('172.16.0.0'))
        self.assertTrue(is_private('172.31.255.255'))
        self.assertFalse(is_private('172.32.0.0'))

        self.assertFalse(is_private('192.167.255.255'))
        self.assertTrue(is_private('192.168.0.0'))
        self.assertTrue(is_private('192.168.255.255'))
        self.assertFalse(is_private('192.169.0.0'))

    def testSort(self):
        from Exscript.util.ipv4 import sort
        import random
        ip_list = ['0.0.0.0',
                   '0.0.0.255',
                   '1.2.3.4',
                   '255.255.0.255',
                   '255.255.255.255',
                   '255.255.255.255']
        ip_list_copy = ip_list[:]
        for i in range(50):
            random.shuffle(ip_list_copy)
            self.assertEqual(ip_list, sort(ip_list_copy))


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(ipv4Test)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
