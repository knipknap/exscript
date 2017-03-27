import sys
import unittest
import re
import os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

import base64
import Exscript.util.file
from tempfile import NamedTemporaryFile

account_pool = [('user1', 'password1'),
                ('user2', 'password2'),
                ('user3', 'password3'),
                ('user4', 'password4')]

hosts = ['localhost', '1.2.3.4', 'ssh://test', 'ssh1://another:23']
expected_hosts = ['localhost', '1.2.3.4', 'test',       'another']


class fileTest(unittest.TestCase):
    CORRELATE = Exscript.util.file

    def setUp(self):
        data = '[account-pool]\n'
        data += 'user1=' + base64.encodebytes(b'password1').decode('utf8') + '\n'
        data += 'user2:' + base64.encodebytes(b'password2').decode('utf8') + '\n'
        data += 'user3 = ' + base64.encodebytes(b'password3').decode('utf8') + '\n'
        data += 'user4 : ' + base64.encodebytes(b'password4').decode('utf8') + '\n'
        self.account_file = NamedTemporaryFile()
        self.account_file.write(data.encode('utf8'))
        self.account_file.flush()

        self.host_file = NamedTemporaryFile()
        self.host_file.write('\n'.join(hosts).encode('utf8'))
        self.host_file.flush()

        content = '\n'.join([h + '	blah' for h in hosts])
        self.csv_host_file = NamedTemporaryFile()
        self.csv_host_file.write(b'hostname	test\n')
        self.csv_host_file.write(content.encode('utf8'))
        self.csv_host_file.flush()

        self.lib_file = NamedTemporaryFile()
        self.lib_file.write(b'__lib__ = {"test": object}\n')
        self.lib_file.flush()

    def tearDown(self):
        self.account_file.close()
        self.host_file.close()
        self.csv_host_file.close()

    def testGetAccountsFromFile(self):
        from Exscript.util.file import get_accounts_from_file
        accounts = get_accounts_from_file(self.account_file.name)
        result = [(a.get_name(), a.get_password()) for a in accounts]
        result.sort()
        self.assertEqual(account_pool, result)

    def testGetHostsFromFile(self):
        from Exscript.util.file import get_hosts_from_file
        result = get_hosts_from_file(self.host_file.name)
        self.assertEqual([h.get_name() for h in result], expected_hosts)

    def testGetHostsFromCsv(self):
        from Exscript.util.file import get_hosts_from_csv
        result = get_hosts_from_csv(self.csv_host_file.name)
        hostnames = [h.get_name() for h in result]
        testvars = [h.get('test')[0] for h in result]
        self.assertEqual(hostnames, expected_hosts)
        self.assertEqual(testvars, ['blah' for h in result])

    def testLoadLib(self):
        from Exscript.util.file import load_lib
        functions = load_lib(self.lib_file.name)
        name = os.path.splitext(os.path.basename(self.lib_file.name))[0]
        self.assertEqual({name + '.test': object}, functions)


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(fileTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
