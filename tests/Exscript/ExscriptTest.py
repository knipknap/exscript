import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

def suite():
    tests = ['testStart', 'testIOSDummy']
    return unittest.TestSuite(map(ExscriptTest, tests))

from termconnect.Dummy import Transport
from Exscript          import Exscript, Connection, Account

show_diag = """
SLOT 0  (RP/LC 0 ): 16 Port ISE Packet Over SONET OC-3c/STM-1 Single Mode/IR LC connector
  MAIN: type 79,  800-19733-08 rev A0
        Deviation: 0
        HW config: 0x01    SW key: 00-00-00
  PCA:  73-7614-07 rev A0 ver 1
        Design Release 1.0  S/N SAL1026SSZX
  MBUS: Embedded Agent
        Test hist: 0x00    RMA#: 00-00-00    RMA hist: 0x00
  DIAG: Test count: 0x00000000    Test results: 0x00000000
  FRU:  Linecard/Module: 16OC3X/POS-IR-LC-B=
        Processor Memory: MEM-LC-ISE-1024=
        Packet Memory: MEM-LC1-PKT-512=(Non-Replaceable)
  L3 Engine: 3 - ISE OC48 (2.5 Gbps)
  MBUS Agent Software version 2.68 (RAM) (ROM version is 3.66)
  ROM Monitor version 18.0
  Fabric Downloader version used 7.1 (ROM version is 7.1)
  Primary clock is CSC 1
  Board is analyzed 
  Board State is Line Card Enabled (IOS  RUN )
  Insertion time: 00:00:30 (36w1d ago)
  Processor Memory size: 1073741824 bytes
  TX Packet Memory size: 268435456 bytes, Packet Memory pagesize: 16384 bytes
  RX Packet Memory size: 268435456 bytes, Packet Memory pagesize: 16384 bytes
  0 crashes since restart
"""

class IOSDummy(Transport):
    def __init__(self, *args, **kwargs):
        Transport.__init__(self, *args, **kwargs)
        self.add_command_handler('show diag .*', self.show_diag)

    def show_diag(self, data):
        match    = re.search(r'(\d+)[\r\n]', data)
        slot     = str(match.group()[0])
        response = show_diag.replace('SLOT 0', 'SLOT ' + slot)
        return response.strip() + '\ntesthost> '

def count_calls(conn, data, **kwargs):
    # Warning: Assertions raised in this function happen in a subprocess!
    assert kwargs.has_key('testarg')
    assert isinstance(conn, Connection)
    data['n_calls'] += 1

def ios_dummy_cb(conn, data, **kwargs):
    # Warning: Assertions raised in this function happen in a subprocess!
    count_calls(conn, data, **kwargs)
    conn.execute('show diag 0')
    assert conn.response.strip() == 'show diag 0\r\n' + show_diag.strip()
    conn.execute('show diag 10')

class ExscriptTest(unittest.TestCase):
    def setUp(self):
        user          = os.environ.get('USER')
        account       = Account(user, '')
        self.exscript = Exscript()
        self.exscript.add_account(account)
        self.exscript.add_protocol('ios', IOSDummy)

    def testStart(self):
        data  = {'n_calls': 0}
        hosts = ['dummy1', 'dummy2']
        self.exscript.start(hosts,    count_calls, data, testarg = 1)
        self.exscript.start('dummy3', count_calls, data, testarg = 1)
        self.exscript.shutdown()
        self.assert_(data['n_calls'] == 3)

        self.exscript.start('dummy4', count_calls, data, testarg = 1)
        self.exscript.shutdown()
        self.assert_(data['n_calls'] == 4)

    def testIOSDummy(self):
        data     = {'n_calls': 0}
        protocol = IOSDummy()
        self.exscript.start('ios:dummy1', ios_dummy_cb, data, testarg = 1)

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
