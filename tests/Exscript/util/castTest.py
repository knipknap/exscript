import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

import Exscript.util.cast
from Exscript import Host

class castTest(unittest.TestCase):
    CORRELATE = Exscript.util.cast

    def testToHost(self):
        from Exscript.util.cast import to_host
        self.assert_(isinstance(to_host('localhost'),       Host))
        self.assert_(isinstance(to_host(Host('localhost')), Host))
        self.assertRaises(Exception, to_host, None)

    def testToHosts(self):
        from Exscript.util.cast import to_hosts
        self.assertRaises(Exception, to_hosts, None)

        result = to_hosts([])
        self.assert_(isinstance(result, list))
        self.assert_(len(result) == 0)

        result = to_hosts('localhost')
        self.assert_(isinstance(result, list))
        self.assert_(len(result) == 1)
        self.assert_(isinstance(result[0], Host))

        result = to_hosts(Host('localhost'))
        self.assert_(isinstance(result, list))
        self.assert_(len(result) == 1)
        self.assert_(isinstance(result[0], Host))

        hosts  = ['localhost', Host('1.2.3.4')]
        result = to_hosts(hosts)
        self.assert_(isinstance(result, list))
        self.assert_(len(result) == 2)
        self.assert_(isinstance(result[0], Host))
        self.assert_(isinstance(result[1], Host))

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(castTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
