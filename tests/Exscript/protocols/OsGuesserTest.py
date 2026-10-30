import os
import re
import unittest

from Exscript.protocols import drivers
from Exscript.protocols.osguesser import OsGuesser


class OsGuesserTest(unittest.TestCase):
    CORRELATE = OsGuesser

    def setUp(self):
        self.sa = OsGuesser()

    def testConstructor(self):
        osg = OsGuesser()
        self.assertIsInstance(osg, OsGuesser)

    def testReset(self):
        self.testSet()
        self.sa.reset()
        self.testSet()

    def testSet(self):
        self.assertEqual(self.sa.get('test'), None)
        self.assertEqual(self.sa.get('test', 0), None)
        self.assertEqual(self.sa.get('test', 50), None)
        self.assertEqual(self.sa.get('test', 100), None)

        self.sa.set('test', 'foo', 0)
        self.assertEqual(self.sa.get('test'), 'foo')
        self.assertEqual(self.sa.get('test', 0), 'foo')
        self.assertEqual(self.sa.get('test', 10), None)

        self.sa.set('test', 'foo', 10)
        self.assertEqual(self.sa.get('test'), 'foo')
        self.assertEqual(self.sa.get('test', 0), 'foo')
        self.assertEqual(self.sa.get('test', 10), 'foo')
        self.assertEqual(self.sa.get('test', 11), None)

        self.sa.set('test', 'foo', 5)
        self.assertEqual(self.sa.get('test'), 'foo')
        self.assertEqual(self.sa.get('test', 0), 'foo')
        self.assertEqual(self.sa.get('test', 10), 'foo')
        self.assertEqual(self.sa.get('test', 11), None)

    def testSetFromMatch(self):
        match_list = (
            (re.compile('on'), 'uno', 50),
            (re.compile('two'), 'doe', 0),
            (re.compile('one'), 'eins', 90),
        )
        self.assertEqual(self.sa.get('test'), None)

        self.sa.set_from_match('test', match_list, '2two2')
        self.assertEqual(self.sa.get('test'), 'doe')

        self.sa.set_from_match('test', match_list, '2one2')
        self.assertEqual(self.sa.get('test'), 'eins')

    def testGet(self):
        pass  # See testSet().

    def testCheckReceivedData(self):
        dirname = os.path.dirname(__file__)
        banner_dir = os.path.join(dirname, 'banners')
        for file in os.listdir(banner_dir):
            if file.startswith('.'):
                continue
            osname = file.split('.')[0]
            if not drivers.driver_map[osname].supports_os_guesser():
                continue
            file = os.path.join(banner_dir, file)
            with open(file) as fp:
                banner = fp.read().rstrip('\n')
            osg = OsGuesser()
            for char in banner:
                osg.check_received_data(char, False)
            self.assertEqual(osg.get('os'), osname)

    def testCheckProtocolInfo(self):
        osg = OsGuesser()
        osg.check_protocol_info('')
        self.assertEqual(osg.get('os'), "unknown")
        osg.check_protocol_info(None)
        self.assertEqual(osg.get('os'), "unknown")
        osg.check_protocol_info("SSH-2.0-Cisco-1.25")
        self.assertEqual(osg.get('os'), "ios")

    def testCheckNetconfCapabilities(self):
        osg = OsGuesser()
        osg.check_netconf_capabilities(
            [
                'urn:ietf:params:netconf:base:1.0',
                'urn:ietf:params:netconf:capability:candidate:1.0',
                'urn:ietf:params:netconf:capability:confirmed-commit:1.0',
                'http://xml.juniper.net/netconf/junos/1.0',
            ]
        )
        self.assertEqual(osg.get('os'), "junos")


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(OsGuesserTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
