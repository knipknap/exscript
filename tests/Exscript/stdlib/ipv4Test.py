import unittest

from interpreter.helpers import TemplateTestCase, split_error

import Exscript.stdlib.ipv4
from Exscript.parselib.exception import ExecuteError


class ipv4Test(TemplateTestCase):
    """
    The IPv4 functions of the template language.
    """

    CORRELATE = Exscript.stdlib.ipv4

    def assertResults(self, *calls):
        for call, expected in calls:
            with self.subTest(call=call):
                self.assertEqual(self.evaluate('{x = %s}' % call)['x'], expected)

    def testInNetwork(self):
        self.assertResults(
            ('ipv4.in_network("10.0.0.0/8", "10.1.2.3")', [True]),
            ('ipv4.in_network("10.0.0.0/8", "11.0.0.1")', [False]),
            ('ipv4.in_network(list.new("10.0.0.0/8", "192.168.0.0/16"), "192.168.5.5")', [True]),
            # Without a prefix length, /24 applies, or the given default.
            ('ipv4.in_network("192.168.1.0", "192.168.1.200")', [True]),
            ('ipv4.in_network("192.168.1.0", "192.168.2.1")', [False]),
            ('ipv4.in_network("192.168.0.0", "192.168.2.1", 16)', [True]),
        )

    def testMask(self):
        self.assertResults(('ipv4.mask("192.168.1.77", "255.255.255.0")', ['192.168.1.0']))
        variables = self.evaluate(
            '{x = ipv4.mask(ips, "255.255.0.0")}', ips=['10.1.2.3', '10.2.3.4']
        )
        self.assertEqual(variables['x'], ['10.1.0.0', '10.2.0.0'])

    def testMask2Pfxlen(self):
        variables = self.evaluate(
            '{x = ipv4.mask2pfxlen(masks)}',
            masks=['255.255.255.0', '255.255.0.0', '255.255.255.252'],
        )
        self.assertEqual(variables['x'], [24, 16, 30])

    def testPfxlen2Mask(self):
        self.assertResults(
            ('ipv4.pfxlen2mask(30)', ['255.255.255.252']),
            ('ipv4.pfxlen2mask("16")', ['255.255.0.0']),
        )

    def testNetwork(self):
        self.assertResults(('ipv4.network("10.1.2.3/8")', ['10.0.0.0']))

    def testBroadcast(self):
        self.assertResults(('ipv4.broadcast("10.1.2.3/8")', ['10.255.255.255']))

    def testPfxmask(self):
        variables = self.evaluate('{x = ipv4.pfxmask(ips, 16)}', ips=['10.1.2.3', '192.168.7.1'])
        self.assertEqual(variables['x'], ['10.1.0.0', '192.168.0.0'])

    def testRemoteIp(self):
        variables = self.evaluate(
            '{x = ipv4.remote_ip(ips)}', ips=['10.0.0.1', '10.0.0.2', '10.0.0.6']
        )
        self.assertEqual(variables['x'], ['10.0.0.2', '10.0.0.1', '10.0.0.5'])

    def testInvalidAddress(self):
        with self.assertRaises(ExecuteError) as cm:
            self.evaluate('{x = ipv4.mask2pfxlen("abc")}')
        lines, marker, message = split_error(cm.exception)
        self.assertEqual((lines, marker), (['{x = ipv4.mask2pfxlen("abc")}'], '     ' + '^' * 16))
        self.assertIn(" while executing function 'ipv4.mask2pfxlen': ", message)


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(ipv4Test)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
