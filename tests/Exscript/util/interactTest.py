import os
import tempfile
import unittest
import unittest.mock

import Exscript.util.interact
from Exscript import Account
from Exscript.util.interact import InputHistory


class InputHistoryTest(unittest.TestCase):
    CORRELATE = InputHistory

    def setUp(self):
        # A file name in a temporary directory: Windows cannot reopen an open temporary file.
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        self.filename = os.path.join(tmpdir.name, 'history')
        self.history = InputHistory(self.filename)

    def testConstructor(self):
        filename = self.filename + '2'
        h = InputHistory()
        h = InputHistory(filename)
        h = InputHistory(filename, 'foo')
        h.set('aaa', 'bbb')
        with open(filename, encoding='utf-8') as fp:
            self.assertEqual(fp.read(), '[foo]\naaa = bbb\n\n')

    def testGet(self):
        self.assertEqual(self.history.get('bar'), None)
        self.assertEqual(self.history.get('bar', None), None)
        self.assertEqual(self.history.get('bar', '...'), '...')
        self.history.set('bar', 'myvalue')
        self.assertEqual(self.history.get('bar'), 'myvalue')
        self.assertEqual(self.history.get('bar', '...'), 'myvalue')
        self.assertEqual(self.history.get('bar', None), 'myvalue')

    def testSet(self):
        self.testGet()
        self.history.set('bar', 'myvalue2')
        self.assertEqual(self.history.get('bar'), 'myvalue2')
        self.assertEqual(self.history.get('bar', '...'), 'myvalue2')
        self.assertEqual(self.history.get('bar', None), 'myvalue2')
        self.history.set('bar', None)
        self.assertEqual(self.history.get('bar'), 'myvalue2')
        self.assertEqual(self.history.get('bar', '...'), 'myvalue2')
        self.assertEqual(self.history.get('bar', None), 'myvalue2')

    def testExistingFile(self):
        with open(self.filename, 'w', encoding='utf-8') as fp:
            fp.write('[script]\nhost = router1\n\n[other]\nhost = router2\n')
        history = InputHistory(self.filename, 'script')
        self.assertEqual(history.get('host'), 'router1')
        history.set('user', 'admin')
        self.assertEqual(InputHistory(self.filename, 'other').get('host'), 'router2')
        self.assertEqual(InputHistory(self.filename, 'script').get('user'), 'admin')


class interactTest(unittest.TestCase):
    CORRELATE = Exscript.util.interact

    def setUp(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        self.tmpdir = tmpdir.name
        self.history = InputHistory(os.path.join(tmpdir.name, 'history'), 'test')

    def typing(self, *answers):
        """Lets input() return the given answers; returns the list of the prompts shown."""
        prompts = []
        answers = iter(answers)

        def fake_input(prompt=''):
            prompts.append(prompt)
            return next(answers)

        patcher = unittest.mock.patch('builtins.input', fake_input)
        patcher.start()
        self.addCleanup(patcher.stop)
        return prompts

    def testPrompt(self):
        prompt = Exscript.util.interact.prompt
        prompts = self.typing('', '  router2  ', '', ' x ')
        self.assertEqual(prompt('host', 'Host', 'router1', history=self.history), 'router1')
        self.assertEqual(self.history.get('host'), 'router1')
        self.assertEqual(prompt('host', 'Host', 'router1', history=self.history), 'router2')
        self.assertEqual(self.history.get('host'), 'router2')

        # With doverh=False, the input from the history is the default.
        self.assertEqual(
            prompt('host', 'Host', 'router1', doverh=False, history=self.history), 'router2'
        )
        self.assertEqual(prompt('path', 'Path', 'x', strip=False, history=self.history), ' x ')
        self.assertEqual(
            prompts, ['Host [router1]: ', 'Host [router1]: ', 'Host [router2]: ', 'Path [x]: ']
        )

    def testPromptHistoryDefaultForEmptyHistory(self):
        prompts = self.typing('')
        value = Exscript.util.interact.prompt(
            'port', 'Port', '22', doverh=False, history=self.history
        )
        self.assertEqual(value, '22')
        self.assertEqual(prompts, ['Port [22]: '])

    def testPromptWithoutDefault(self):
        # Without a default, or with an empty one, also from the history, none is offered.
        prompt = Exscript.util.interact.prompt
        prompts = self.typing('', '', '', '', 'admin', '')
        self.assertEqual(prompt('host', 'Host', history=self.history), '')
        self.assertEqual(self.history.get('host'), '')
        self.assertEqual(prompt('host', 'Host', history=self.history), '')
        self.assertEqual(prompt('port', 'Port', doverh=False, history=self.history), '')
        self.assertEqual(prompt('path', 'Path', '', history=self.history), '')
        self.assertEqual(prompt('user', 'User', history=self.history), 'admin')
        self.assertEqual(prompt('user', 'User', history=self.history), 'admin')
        self.assertEqual(
            prompts, ['Host: ', 'Host: ', 'Port: ', 'Path: ', 'User: ', 'User [admin]: ']
        )

    def testPromptCheck(self):
        def check(value):
            if len(value) < 4:
                return ['Too short.', 'Please enter at least 4 characters.']
            return None

        prompts = self.typing('abc', 'abcd')
        with unittest.mock.patch('builtins.print') as output:
            value = Exscript.util.interact.prompt(
                'name', 'Name', 'abc', check=check, history=self.history
            )
        self.assertEqual(value, 'abcd')
        self.assertEqual(prompts, ['Name [abc]: ', 'Name [abc]: '])
        output.assert_called_once_with('Too short.\nPlease enter at least 4 characters.')
        self.assertEqual(self.history.get('name'), 'abcd')  # only the accepted input

    def testPromptWithoutHistory(self):
        # The input is stored in ~/.exscript_history.
        self.typing('router1')
        with unittest.mock.patch.dict(
            os.environ, {'HOME': self.tmpdir, 'USERPROFILE': self.tmpdir}
        ):
            value = Exscript.util.interact.prompt('host', 'Host', 'r')
        self.assertEqual(value, 'router1')
        with open(os.path.join(self.tmpdir, '.exscript_history'), encoding='utf-8') as fp:
            self.assertIn('host = router1', fp.read())

    def testGetFilename(self):
        # A name of a file that does not exist is rejected, and the prompt repeats.
        existing = os.path.join(self.tmpdir, 'hosts.txt')
        with open(existing, 'w', encoding='utf-8'):
            pass
        history = InputHistory(os.path.join(self.tmpdir, 'history'))
        missing = os.path.join(self.tmpdir, 'missing.txt')
        prompts = self.typing(missing, '  ' + existing + '  ')
        with unittest.mock.patch('builtins.print') as output:
            filename = Exscript.util.interact.get_filename('hosts', 'Host file', history=history)
        self.assertEqual(filename, existing)
        output.assert_called_once_with('File not found. Please enter a filename.')
        self.assertEqual(history.get('hosts'), existing)
        self.assertEqual(prompts, ['Host file: '] * 2)

    def testGetUser(self):
        get_user = Exscript.util.interact.get_user
        prompts = self.typing('', 'bob', '')
        with unittest.mock.patch('getpass.getuser', return_value='alice'):
            self.assertEqual(get_user(), 'alice')
            self.assertEqual(get_user(), 'bob')
            self.assertEqual(get_user('Login'), 'alice')
        self.assertEqual(
            prompts,
            [
                'Please enter your user name [alice]: ',
                'Please enter your user name [alice]: ',
                'Login [alice]: ',
            ],
        )

    def testGetUserWithoutDefault(self):
        prompts = self.typing('carol', 'dave')
        with unittest.mock.patch('getpass.getuser', return_value=''):
            self.assertEqual(Exscript.util.interact.get_user(), 'carol')
        with unittest.mock.patch('getpass.getuser', side_effect=KeyError('no such user')):
            self.assertEqual(Exscript.util.interact.get_user(), 'dave')
        self.assertEqual(prompts, ['Please enter your user name: '] * 2)

    def testGetUserWithoutUserName(self):
        # getuser() raises OSError since Python 3.13, KeyError before, if it finds no name.
        errors = OSError('No username set in the environment'), KeyError('uid not found: 1000')
        for error in errors:
            prompts = self.typing('carol', 'dave', 'erin')
            with (
                unittest.mock.patch('getpass.getuser', side_effect=error),
                unittest.mock.patch('getpass.getpass', return_value='S3cr3t'),
            ):
                self.assertEqual(Exscript.util.interact.get_user(), 'carol')
                self.assertEqual(Exscript.util.interact.get_login(), ('dave', 'S3cr3t'))
                self.assertEqual(Exscript.util.interact.read_login().get_name(), 'erin')
            self.assertEqual(prompts, ['Please enter your user name: '] * 3)

    def testGetLogin(self):
        prompts = self.typing('')
        with (
            unittest.mock.patch('getpass.getuser', return_value='alice'),
            unittest.mock.patch('getpass.getpass', return_value='S3cr3t') as getpass,
        ):
            self.assertEqual(Exscript.util.interact.get_login(), ('alice', 'S3cr3t'))
        getpass.assert_called_once_with('Please enter your password: ')  # not echoed
        self.assertEqual(len(prompts), 1)

    def testReadLogin(self):
        self.typing('bob')
        with (
            unittest.mock.patch('getpass.getuser', return_value='alice'),
            unittest.mock.patch('getpass.getpass', return_value='S3cr3t'),
        ):
            account = Exscript.util.interact.read_login()
        self.assertIsInstance(account, Account)
        self.assertEqual(account.get_name(), 'bob')
        self.assertEqual(account.get_password(), 'S3cr3t')


def suite():
    loader = unittest.TestLoader()
    thesuite = unittest.TestSuite()
    thesuite.addTest(loader.loadTestsFromTestCase(InputHistoryTest))
    thesuite.addTest(loader.loadTestsFromTestCase(interactTest))
    return thesuite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
