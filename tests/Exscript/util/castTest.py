import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

import Exscript.util.cast
import re
from Exscript         import Host
from Exscript.Log     import Log
from Exscript.Logfile import Logfile

class castTest(unittest.TestCase):
    CORRELATE = Exscript.util.cast

    def testToList(self):
        from Exscript.util.cast import to_list
        self.assertEqual(to_list(None),     [None])
        self.assertEqual(to_list([]),       [])
        self.assertEqual(to_list('test'),   ['test'])
        self.assertEqual(to_list(['test']), ['test'])

    def testToHost(self):
        from Exscript.util.cast import to_host
        self.assert_(isinstance(to_host('localhost'),       Host))
        self.assert_(isinstance(to_host(Host('localhost')), Host))
        self.assertRaises(TypeError, to_host, None)

    def testToHosts(self):
        from Exscript.util.cast import to_hosts
        self.assertRaises(TypeError, to_hosts, None)

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

    def testToRegex(self):
        from Exscript.util.cast import to_regex
        self.assert_(hasattr(to_regex('regex'), 'match'))
        self.assert_(hasattr(to_regex(re.compile('regex')), 'match'))
        self.assertRaises(TypeError, to_regex, None)

    def testToRegexs(self):
        from Exscript.util.cast import to_regexs
        self.assertRaises(TypeError, to_regexs, None)

        result = to_regexs([])
        self.assert_(isinstance(result, list))
        self.assert_(len(result) == 0)

        result = to_regexs('regex')
        self.assert_(isinstance(result, list))
        self.assert_(len(result) == 1)
        self.assert_(hasattr(result[0], 'match'))

        result = to_regexs(re.compile('regex'))
        self.assert_(isinstance(result, list))
        self.assert_(len(result) == 1)
        self.assert_(hasattr(result[0], 'match'))

        regexs = ['regex1', re.compile('regex2')]
        result = to_regexs(regexs)
        self.assert_(isinstance(result, list))
        self.assert_(len(result) == 2)
        self.assert_(hasattr(result[0], 'match'))
        self.assert_(hasattr(result[1], 'match'))
        self.assertEqual(result[0].pattern, 'regex1')
        self.assertEqual(result[1].pattern, 'regex2')

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(castTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
