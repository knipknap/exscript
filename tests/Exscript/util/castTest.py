import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

import Exscript.util.cast
from Exscript         import Host
from Exscript.Log     import Log
from Exscript.Logfile import Logfile

class castTest(unittest.TestCase):
    CORRELATE = Exscript.util.cast

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

    def testToLog(self):
        from Exscript.util.cast import to_log
        self.assert_(isinstance(to_log('log'),          Logfile))
        self.assert_(isinstance(to_log(Logfile('log')), Logfile))
        self.assert_(isinstance(to_log(Log()),          Log))
        self.assert_(not isinstance(to_log(Log()),      Logfile))
        self.assertRaises(TypeError, to_log, None)

    def testToLogs(self):
        from Exscript.util.cast import to_logs
        self.assertRaises(TypeError, to_logs, None)

        result = to_logs([])
        self.assert_(isinstance(result, list))
        self.assert_(len(result) == 0)

        result = to_logs('log')
        self.assert_(isinstance(result, list))
        self.assert_(len(result) == 1)
        self.assert_(isinstance(result[0], Logfile))

        result = to_logs(Log())
        self.assert_(isinstance(result, list))
        self.assert_(len(result) == 1)
        self.assert_(isinstance(result[0], Log))
        self.assert_(not isinstance(result[0], Logfile))

        logs  = ['locallog', Log()]
        result = to_logs(logs)
        self.assert_(isinstance(result, list))
        self.assert_(len(result) == 2)
        self.assert_(isinstance(result[0], Logfile))
        self.assert_(isinstance(result[1], Log))

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(castTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
