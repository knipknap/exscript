import base64
import os.path
import unittest
from tempfile import NamedTemporaryFile

import Exscript.util.file

account_pool = [
    ('user1', 'password1'),
    ('user2', 'password2'),
    ('user3', 'password3'),
    ('user4', 'password4'),
]

hosts = ['localhost', '1.2.3.4', 'ssh://test', 'telnet://another:23']
expected_hosts = ['localhost', '1.2.3.4', 'test', 'another']


class fileTest(unittest.TestCase):
    CORRELATE = Exscript.util.file

    def setUp(self):
        data = '[account-pool]\n'
        data += 'user1=' + base64.encodebytes(b'password1').decode('utf8') + '\n'
        data += 'user2:' + base64.encodebytes(b'password2').decode('utf8') + '\n'
        data += 'user3 = ' + base64.encodebytes(b'password3').decode('utf8') + '\n'
        data += 'user4 : ' + base64.encodebytes(b'password4').decode('utf8') + '\n'
        self.account_file = self.write_tempfile(data.encode('utf8'))
        self.host_file = self.write_tempfile('\n'.join(hosts).encode('utf8'))
        content = '\n'.join([h + '	blah' for h in hosts])
        self.csv_host_file = self.write_tempfile(b'hostname	test\n' + content.encode('utf8'))
        self.lib_file = self.write_tempfile(b'__lib__ = {"test": object}\n')

    def write_tempfile(self, data):
        # Closed before the test opens it by name, which Windows requires.
        file = NamedTemporaryFile(delete=False)
        with file:
            file.write(data)
        self.addCleanup(os.remove, file.name)
        return file

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
