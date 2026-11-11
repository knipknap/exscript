import base64
import os.path
import re
import tempfile
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

    def testMissingFiles(self):
        from Exscript.util.file import get_hosts_from_csv, get_hosts_from_file, load_lib

        tmpdir = self.enterContext(tempfile.TemporaryDirectory())
        filename = os.path.join(tmpdir, 'missing')
        for func in get_hosts_from_file, get_hosts_from_csv, load_lib:
            with self.subTest(func=func.__name__):
                with self.assertRaisesRegex(OSError, 'No such file: ' + re.escape(filename)):
                    func(filename)

    def testGetAccountsFromFileWithOtherSections(self):
        from Exscript.util.file import get_accounts_from_file

        data = '[other]\nuser9 = cGFzc3dvcmQ=\n[account-pool]\nAdmin = cGFzc3dvcmQ=\n'
        accounts = get_accounts_from_file(self.write_tempfile(data.encode('utf8')).name)
        self.assertEqual(
            [(a.get_name(), a.get_password()) for a in accounts], [('Admin', 'password')]
        )

    def testGetAccountsFromFileWithInvalidPasswords(self):
        from Exscript.util.file import get_accounts_from_file

        for password in 'not base64!', base64.b64encode(b'\xffpassword').decode('ascii'):
            with self.subTest(password=password):
                data = '[account-pool]\nuser1 = %s\n' % password
                filename = self.write_tempfile(data.encode('utf8')).name
                with self.assertRaisesRegex(Exception, 'Could not decode password for user: user1'):
                    get_accounts_from_file(filename)

    def testGetAccountsFromFileWithPasswordEncoding(self):
        from Exscript.util.file import get_accounts_from_file

        password = base64.b64encode('pässword'.encode('latin-1')).decode('ascii')
        data = '[account-pool]\nuser1 = %s\n' % password
        filename = self.write_tempfile(data.encode('utf8')).name
        accounts = get_accounts_from_file(filename, password_encoding='latin-1')
        self.assertEqual(accounts[0].get_password(), 'pässword')

    def testGetHostsFromFileWithCommentsAndDuplicates(self):
        from Exscript.util.file import get_hosts_from_file

        data = '# core routers\nrouter1\n\nrouter2  # backup\nrouter1\ntelnet://switch1\n'
        filename = self.write_tempfile(data.encode('utf8')).name
        hosts = get_hosts_from_file(filename, default_protocol='telnet')
        self.assertEqual(
            [h.get_name() for h in hosts], ['router1', 'router2', 'router1', 'switch1']
        )
        self.assertEqual({h.get_protocol() for h in hosts}, {'telnet'})
        hosts = get_hosts_from_file(filename, remove_duplicates=True, default_domain='example.com')
        self.assertEqual(
            [(h.get_protocol(), h.get_address()) for h in hosts],
            [
                ('ssh', 'router1.example.com'),
                ('ssh', 'router2.example.com'),
                ('telnet', 'switch1.example.com'),
            ],
        )

    def testGetHostsFromCsvWithInvalidHeader(self):
        from Exscript.util.file import get_hosts_from_csv

        for header, error in (
            ('name\tvar', 'File does not start with "hostname" or "address".'),
            ('address var', 'Make sure to separate columns by tabs.'),
            ('address\t\tvar', 'Make sure to separate columns by tabs.'),
        ):
            with self.subTest(header=header):
                filename = self.write_tempfile((header + '\n1.2.3.4\tvalue\n').encode('utf8')).name
                with self.assertRaisesRegex(Exception, re.escape(error)):
                    get_hosts_from_csv(filename)

    def testGetHostsFromCsvWithSeveralLinesPerHost(self):
        # The example of the documentation, with an empty line and a missing value.
        from Exscript.util.file import get_hosts_from_csv

        data = (
            'address\thostname\ttestvar1\ttestvar2\n'
            '10.0.0.1\tmyhost\tvalue1\tothervalue\n'
            '\n'
            '10.0.0.1\tmyhost\tvalue2\tothervalue2\n'
            '10.0.0.2\totherhost\tfoo\n'
        )
        filename = self.write_tempfile(data.encode('utf8')).name
        hosts = get_hosts_from_csv(filename, default_protocol='telnet')
        self.assertEqual([h.get_address() for h in hosts], ['10.0.0.1', '10.0.0.2'])
        self.assertEqual([h.get_name() for h in hosts], ['myhost', 'otherhost'])
        self.assertEqual([h.get_protocol() for h in hosts], ['telnet', 'telnet'])
        self.assertEqual(hosts[0].get('testvar1'), ['value1', 'value2'])
        self.assertEqual(hosts[0].get('testvar2'), ['othervalue', 'othervalue2'])
        self.assertEqual(hosts[1].get('testvar1'), ['foo'])
        self.assertEqual(hosts[1].get('testvar2'), [''])


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(fileTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
