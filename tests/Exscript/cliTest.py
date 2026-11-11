import contextlib
import io
import os
import re
import runpy
import signal
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest import mock

from Exscript import Account, Host, PrivateKey
from Exscript.cli import (
    _create_output,
    _duration,
    _exit_on_sigint,
    _expand_bracket,
    _Output,
    _RichOutput,
    main,
    otp_main,
)
from Exscript.interpreter.exception import FailException
from Exscript.parselib.exception import CompileError
from Exscript.protocols import Dummy, drivers
from Exscript.util import template
from Exscript.util.crypt import otp
from Exscript.workqueue.job import Thread

try:
    from rich.console import Console
except ImportError:  # the optional "cli" extra is not installed
    Console = None

requires_rich = unittest.skipIf(Console is None, 'requires the "cli" extra')

KEYFILE = os.path.join(os.path.dirname(__file__), 'protocols', 'id_rsa')
HELLO = '{sys.message("hello")}'
POOL = '[account-pool]\nalice = c2VjcmV0\n'  # the password is "secret"
RED, YELLOW, GREEN, BOLD, RESET = '\x1b[31m', '\x1b[33m', '\x1b[32m', '\x1b[1m', '\x1b[0m'

LIB = '''
def hello(scope, name):
    print('hello', name[0])
    return True


__lib__ = {'hello': hello}
'''

DRIVER = '''
from Exscript.protocols.drivers import Driver


class CliTestDriver(Driver):
    def __init__(self):
        Driver.__init__(self, 'cli_test')
'''


class Tty(io.StringIO):
    """A file that claims to be a terminal."""

    def isatty(self):
        return True


@contextlib.contextmanager
def environ(**values):
    """Sets the given environment variables, and removes the others that rich reads to
    detect a terminal and its colors."""
    with mock.patch.dict(os.environ, values):
        names = {'NO_COLOR', 'FORCE_COLOR', 'TTY_COMPATIBLE', 'TTY_INTERACTIVE', 'TERM'}
        for name in names - values.keys():
            os.environ.pop(name, None)
        yield


def terminal():
    """Returns a rich console that writes to a StringIO like to a terminal with 16 colors
    and 100 columns, whatever the environment says."""
    return Console(
        file=io.StringIO(),
        width=100,
        force_terminal=True,
        force_interactive=True,
        color_system='standard',
        no_color=False,
        legacy_windows=False,
    )


def shown(output):
    """Returns what a terminal shows of the given output: without the states of the
    progress display that are erased, and without styles and other control sequences."""
    output = re.sub(r'[^\n]*\r\x1b\[2K', '', output)
    return re.sub(r'\x1b\[[0-9;?]*[A-Za-z]', '', output)


class cliTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        # main() sets up the logging of the process and the debug level of the templates.
        self.setup_logging = self.start(mock.patch('Exscript.cli.setupLogging'))
        self.start(mock.patch.object(template, 'debug', 0))
        self.start(mock.patch.dict(os.environ, NO_COLOR='1'))

    def start(self, patcher):
        """Starts the given patcher until the end of the test, and returns its mock."""
        result = patcher.start()
        self.addCleanup(patcher.stop)
        return result

    def path(self, *names):
        """Returns the path of the given file in the temporary directory."""
        return os.path.join(self.tmpdir.name, *names)

    def write(self, name, text):
        """Writes the given text to the given file in the temporary directory."""
        with open(self.path(name), 'w', encoding='utf-8') as fp:
            fp.write(text)
        return self.path(name)

    def read(self, *names):
        """Returns the content of the given file in the temporary directory."""
        with open(self.path(*names), encoding='utf-8') as fp:
            return fp.read()

    def run_main(self, *args):
        """Runs main() with the given arguments, and returns the exit status and the output."""
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                code = main(list(args))
            except SystemExit as e:
                code = e.code
        return code, stdout.getvalue(), stderr.getvalue()

    def unload_driver(self, name):
        """Unregisters the driver with the given name if it is registered."""
        if name in drivers.driver_map:
            drivers.disable_driver(name)

    def rich_output(self):
        """Lets main() and otp_main() write with rich to terminals, and returns the output
        and the files of its stdout and stderr."""
        self.start(mock.patch.dict(os.environ, TERM='xterm'))  # not a dumb terminal
        stdout, stderr = terminal(), terminal()
        output = _RichOutput(stdout, stderr)
        self.start(mock.patch('Exscript.cli._create_output', return_value=output))
        return output, stdout.file, stderr.file

    def testTemplateFile(self):
        path = self.write('test.exscript', '{sys.message(__filename__)}\n')
        code, stdout, stderr = self.run_main('-n', '-i', path, 'dummy://r1')
        self.assertEqual(code, 0, stderr)
        self.assertEqual(stdout, path + '\n')

    def testExecuteTakesTheFilenameAsHost(self):
        script = '{sys.message(__hostname__)}'
        args = '-n', '-i', '-c', '2', '-e', script, 'dummy://r1', 'dummy://r2'
        code, stdout, stderr = self.run_main(*args)
        self.assertEqual(code, 0, stderr)
        self.assertEqual(sorted(stdout.splitlines()), ['r1', 'r2'])

    def testExecuteHasNoFilename(self):
        for args in ('-n', '-i'), ('-n', '-i', '--no-prompt'):
            code, stdout, stderr = self.run_main(
                *args, '-e', '{sys.message(__filename__)}', 'dummy://r1'
            )
            self.assertEqual(code, 0, stderr)
            self.assertEqual(stdout, 'undefined\n')

    def testProtocolAndDefaultDomain(self):
        args = '-n', '-i', '-p', 'dummy', '--default-domain', 'example.com'
        code, stdout, stderr = self.run_main(*args, '-e', '{sys.message(__hostname__)}', 'r1')
        self.assertEqual(code, 0, stderr)
        self.assertEqual(stdout, 'r1.example.com\n')

    def testTemplateErrors(self):
        cases = (
            ((), 'Missing template filename'),
            ((self.path('missing.exscript'), 'dummy://r1'), 'No such file or directory'),
            (('-e', HELLO), 'No hosts to connect to'),
            (('-e', '{sys.message(}', 'dummy://r1'), 'Expected term but got close_curly_bracket'),
            (('-e', '{sys.env("PATH")}', 'dummy://r1'), "function 'sys.env' is not permitted"),
        )
        for args, error in cases:
            code, stdout, stderr = self.run_main('-n', '-i', *args)
            self.assertEqual(code, 2, stderr)
            self.assertIn(error, stderr)

    def testInsecure(self):
        code, stdout, stderr = self.run_main(
            '-n', '-i', '--insecure', '-e', '{sys.env("PATH")}', 'dummy://r1'
        )
        self.assertEqual(code, 0, stderr)

    def testParserDebugging(self):
        code, stdout, stderr = self.run_main('-n', '-i', '-V', '1', '-e', HELLO, 'dummy://r1')
        self.assertEqual(code, 0, stderr)
        self.assertTrue(stdout.endswith('hello\n'), stdout)
        # With -V, an error in the template raises the exception with its traceback.
        with self.assertRaises(CompileError):
            self.run_main('-n', '-i', '-V', '1', '-e', '{sys.message(}', 'dummy://r1')

    def testVerbosity(self):
        self.run_main('-n', '-i', '-e', HELLO, 'dummy://r1')
        self.setup_logging.assert_called_once_with(package=True, parser=False, protocol=False)
        args = '-v', '0', '-V', '1', '--protocol-verbose', '1'
        self.run_main('-n', '-i', *args, '-e', HELLO, 'dummy://r1')
        self.setup_logging.assert_called_with(package=False, parser=True, protocol=True)

    def testHostFilesWithUserAndVariables(self):
        # The shell expands neither in quotes, e.g. --hosts '~/$SITE/hosts.txt'.
        os.mkdir(self.path('hosts'))
        self.write(os.path.join('hosts', 'hosts.txt'), 'dummy://r1\n')
        self.write(os.path.join('hosts', 'hosts.csv'), 'address\tgreeting\ndummy://r2\thello\n')
        env = {'HOME': self.tmpdir.name, 'USERPROFILE': self.tmpdir.name, 'SITE': 'hosts'}
        cases = (
            ('--hosts', 'hosts.txt', '{sys.message("hello")}'),
            ('--csv-hosts', 'hosts.csv', '{sys.message(greeting)}'),
        )
        with mock.patch.dict(os.environ, env):
            for option, name, script in cases:
                code, stdout, stderr = self.run_main(
                    '-n', '-i', '-e', script, option, '~/$SITE/' + name
                )
                self.assertEqual(code, 0, stderr)
                self.assertEqual(stdout, 'hello\n')

    def testEmptyHostFiles(self):
        for option, name, text in (
            ('--hosts', 'hosts.txt', ''),
            ('--csv-hosts', 'hosts.csv', 'address\n'),
        ):
            path = self.write(name, text)
            code, stdout, stderr = self.run_main(
                '-n', '-i', '-e', HELLO, option, path, 'dummy://r1'
            )
            self.assertEqual(code, 0, stderr)
            self.assertEqual(stdout, f'Warning: {path} is empty.\nhello\n')

    def testHostFileErrors(self):
        cases = (
            ('--hosts', self.path('missing.txt'), 'No such file'),
            ('--csv-hosts', self.path('missing.csv'), 'No such file'),
            ('--hosts', self.write('hosts.txt', 'dummy://r1:port\n'), 'Hostname parse error'),
        )
        for option, path, error in cases:
            code, stdout, stderr = self.run_main('-n', '-i', '-e', HELLO, option, path)
            self.assertEqual(code, 2, stderr)
            self.assertIn(error, stderr)

    def testHostVariablePrompt(self):
        path = self.write('hosts.csv', 'address\tgreeting\ndummy://r1\t{Greeting}\n')
        script = '{sys.message(greeting)}'
        with mock.patch('builtins.input', return_value='hello') as input:
            code, stdout, stderr = self.run_main('-n', '-i', '-e', script, '--csv-hosts', path)
        self.assertEqual(code, 0, stderr)
        self.assertEqual(stdout, 'hello\n')
        input.assert_called_once_with('Please enter Greeting: ')

    def testDefinePrompts(self):
        args = '-d', 'a={A}', '-d', 'b={!B}', '-d', 'c={#C}', '-d', 'd={}'
        script = '{sys.message(a)}{sys.message(b)}{sys.message(c)}{sys.message(d)}'
        with (
            mock.patch('builtins.input', side_effect=['x', '"y"', 'z']) as input,
            mock.patch('getpass.getpass', return_value='secret') as getpass,
        ):
            code, stdout, stderr = self.run_main('-n', '-i', *args, '-e', script, 'dummy://r1')
        self.assertEqual(code, 0, stderr)
        self.assertEqual(stdout, 'x\nsecret\ny\nz\n')
        prompts = [call.args[0] for call in input.call_args_list]
        self.assertEqual(
            prompts, ['Please enter A: ', 'Please enter C: ', "Please enter a value for 'd' : "]
        )
        getpass.assert_called_once_with('Please enter B: ')

    def testDefineErrors(self):
        cases = (
            ('a', 'invalid value: a'),
            ('__filename__=x', "Assignment to internal variable '__filename__'"),
        )
        for value, error in cases:
            code, stdout, stderr = self.run_main('-n', '-i', '-d', value, '-e', HELLO, 'dummy://r1')
            self.assertEqual(code, 2, stderr)
            self.assertIn(error, stderr)

    def testDefineValueWithEqualSign(self):
        script = '{sys.message(a)}'
        code, stdout, stderr = self.run_main('-n', '-i', '-d', 'a=b=c', '-e', script, 'dummy://r1')
        self.assertEqual(code, 0, stderr)
        self.assertEqual(stdout, 'b=c\n')

    def testLoginPrompt(self):
        with (
            mock.patch('builtins.input', return_value='joe') as input,
            mock.patch('getpass.getpass', return_value='secret') as getpass,
        ):
            code, stdout, stderr = self.run_main('-e', '{sys.message(__username__)}', 'dummy://r1')
        self.assertEqual(code, 0, stderr)
        self.assertEqual(stdout, 'joe\n')
        self.assertTrue(input.call_args.args[0].startswith('Please enter your user name'))
        getpass.assert_called_once_with('Please enter your password: ')

    def testLoginPromptInterrupted(self):
        with mock.patch('builtins.input', side_effect=KeyboardInterrupt):
            code, stdout, stderr = self.run_main('-e', HELLO, 'dummy://r1')
        self.assertEqual(code, 1)
        self.assertEqual(stdout, '')

    def testNoAuthentication(self):
        # As the help says, -n skips only the automatic login: without -i, the command asks
        # for the login, and the template can log in with it.
        code, stdout, stderr = self.run_main('--help')
        words = ' '.join(stdout.split())
        help = words[words.index('-n, --no-authentication') : words.index('--authorization ')]
        expected = (
            '-n, --no-authentication Skip the automatic login. Unless -i is given, the command'
            ' still asks for a username and password, so that the template can log in itself'
            ' with them, e.g. with connection.authenticate(). '
        )
        self.assertEqual(help, expected)

        script = '{connection.authenticate()}{sys.message("logged in")}'
        with (
            mock.patch('builtins.input', return_value='joe'),
            mock.patch('getpass.getpass', return_value='secret'),
        ):
            code, stdout, stderr = self.run_main(
                '-n', '-l', self.path('logs'), '-e', script, 'dummy://r1'
            )
        self.assertEqual(code, 0, stderr)
        self.assertTrue(stdout.endswith('logged in\n'), stdout)
        self.assertIn('User: joe', self.read('logs', 'r1.log'))

    def testAuthorizationPrompt(self):
        with (
            mock.patch('builtins.input', return_value='joe'),
            mock.patch('getpass.getpass', side_effect=['secret', 'enable']) as getpass,
        ):
            code, stdout, stderr = self.run_main('--authorization', '-e', HELLO, 'dummy://r1')
        self.assertEqual(code, 0, stderr)
        prompts = [call.args[0] for call in getpass.call_args_list]
        expected = ['Please enter your password: ', 'Please enter your authorization password: ']
        self.assertEqual(prompts, expected)

    def testAccountPool(self):
        pool = self.write('pool.cfg', POOL)
        script = '{sys.message(__username__)}'
        with mock.patch('builtins.input') as input, mock.patch('getpass.getpass') as getpass:
            code, stdout, stderr = self.run_main('--account-pool', pool, '-e', script, 'dummy://r1')
        self.assertEqual(code, 0, stderr)
        self.assertEqual(stdout, 'alice\n')
        input.assert_not_called()
        getpass.assert_not_called()

    def testEmptyAccountPool(self):
        pool = self.write('pool.cfg', '[account-pool]\n')
        code, stdout, stderr = self.run_main(
            '-n', '-i', '--account-pool', pool, '-e', HELLO, 'dummy://r1'
        )
        self.assertEqual(code, 0, stderr)
        self.assertEqual(
            stdout, f'WARNING: No accounts found in account pool file ({pool})!\nhello\n'
        )

    def testSshKey(self):
        with (
            mock.patch('builtins.input', return_value='joe'),
            mock.patch('getpass.getpass', return_value='secret'),
        ):
            script = '{sys.message(__username__)}'
            code, stdout, stderr = self.run_main('--ssh-key', KEYFILE, '-e', script, 'dummy://r1')
        self.assertEqual(code, 0, stderr)
        self.assertEqual(stdout, f'Reading key from {KEYFILE}\njoe\n')

    def testSshKeyWithoutLoginPrompt(self):
        # The key is for the current user; without a user name, there is no account.
        cases = (
            (mock.patch('getpass.getuser', return_value='jane'), [('jane', None, None)]),
            (mock.patch('getpass.getuser', side_effect=OSError('no user name')), []),  # 3.13+
            (mock.patch('getpass.getuser', side_effect=KeyError('no user name')), []),
        )
        for getuser, expected in cases:
            with getuser, mock.patch('Exscript.cli.Account', wraps=Account) as account:
                code, stdout, stderr = self.run_main(
                    '-n', '-i', '--ssh-key', KEYFILE, '-e', HELLO, 'dummy://r1'
                )
            self.assertEqual(code, 0, stderr)
            self.assertEqual(stdout, f'Reading key from {KEYFILE}\nhello\n')
            self.assertEqual([call.args for call in account.call_args_list], expected)
            for call in account.call_args_list:
                self.assertIsInstance(call.kwargs['key'], PrivateKey)

    def testSshKeyAtAPasswordPrompt(self):
        # The dummy device asks for a password, which the account with the key lacks.
        args = '-i', '--ssh-key', KEYFILE, '-l', self.path('logs'), '-e', HELLO, 'dummy://r1'
        with mock.patch('getpass.getuser', return_value='jane'):
            code, stdout, stderr = self.run_main(*args)
        self.assertEqual(code, 1)
        self.assertEqual(stderr, 'error: 1 actions failed.\n')
        error = self.read('logs', 'r1.log.error')
        self.assertIn(
            'LoginFailure: The device asks for a password, but the account has none', error
        )

    def testInvalidSshKey(self):
        key = self.write('id_invalid', 'not a key\n')
        code, stdout, stderr = self.run_main(
            '-n', '-i', '--ssh-key', key, '-e', HELLO, 'dummy://r1'
        )
        self.assertEqual(code, 2, stderr)
        self.assertIn('not a recognized private key', stderr)

    def testSshOptions(self):
        args = (
            ('--ssh-disabled-algs', 'ciphers=aes128-cbc,3des-cbc;pubkeys=ssh-rsa'),
            ('--ssh-preferred-auth', 'publickey,password'),
            ('--ssh-auto-verify',),
            ('--ssh-host-key-policy', 'warn'),
        )
        expected = {
            'disabled_algorithms': {'ciphers': ['aes128-cbc', '3des-cbc'], 'pubkeys': ['ssh-rsa']},
            'preferred_authentications': ['publickey', 'password'],
            'verify_fingerprint': False,
            'host_key_policy': 'warn',
        }
        defaults = {'verify_fingerprint': True, 'host_key_policy': 'reject'}
        for options, want in ((), defaults), (sum(args, ()), expected):
            with mock.patch.object(
                Host, 'set_option', autospec=True, side_effect=Host.set_option
            ) as set_option:
                code, stdout, stderr = self.run_main(
                    '-n', '-i', *options, '-e', HELLO, 'dummy://r1'
                )
            self.assertEqual(code, 0, stderr)
            got = {call.args[1]: call.args[2] for call in set_option.call_args_list}
            got.pop('debug')
            self.assertEqual(got, want)

    def testNoPrompt(self):
        # The commands are sent without waiting for a prompt; the device asks for the login.
        template = self.write('test.exscript', 'ls\n{sys.message(__filename__)}\n')
        code, stdout, stderr = self.run_main('-n', '-i', '--no-prompt', template, 'dummy://r1')
        self.assertEqual(code, 0, stderr)
        self.assertEqual(stdout, template + '\n')

        hosts = self.write('hosts.txt', 'dummy://r1\n')
        script = 'ls\n{sys.message("sent")}'
        code, stdout, stderr = self.run_main(
            '-n', '-i', '--no-prompt', '-e', script, '--hosts', hosts
        )
        self.assertEqual(code, 0, stderr)
        self.assertEqual(stdout, 'sent\n')

    def testNoStrip(self):
        pool = self.write('pool.cfg', POOL)
        script = 'ls\n{sys.message(__response__)}'
        for args, expected in ((), '\n'), (('--no-strip',), 'ls\n'):
            code, stdout, stderr = self.run_main(
                '--account-pool', pool, *args, '-e', script, 'dummy://r1'
            )
            self.assertEqual(code, 0, stderr)
            self.assertEqual(stdout, expected)

    def testNoEscaping(self):
        script = r'{sys.message("A\x42C")}'
        for args, expected in ((), 'ABC\n'), (('--no-escaping',), 'Ax42C\n'):
            code, stdout, stderr = self.run_main('-n', '-i', *args, '-e', script, 'dummy://r1')
            self.assertEqual(code, 0, stderr)
            self.assertEqual(stdout, expected)

    def testNoAutoLogout(self):
        # The template logs out (close without force) before the queue closes the connection.
        for args, forced in ((), [False, True]), (('--no-auto-logout',), [True]):
            with mock.patch.object(Dummy, 'close', autospec=True, side_effect=Dummy.close) as close:
                code, stdout, stderr = self.run_main('-n', '-i', *args, '-e', HELLO, 'dummy://r1')
            self.assertEqual(code, 0, stderr)
            self.assertEqual([call.kwargs['force'] for call in close.call_args_list], forced)

    def testLib(self):
        lib = self.write('mylib.py', LIB)
        script = '{mylib.hello("world")}'
        code, stdout, stderr = self.run_main('-n', '-i', '--lib', lib, '-e', script, 'dummy://r1')
        self.assertEqual(code, 0, stderr)
        self.assertEqual(stdout, 'hello world\n')

        missing = self.path('missing.py')
        code, stdout, stderr = self.run_main(
            '-n', '-i', '--lib', missing, '-e', HELLO, 'dummy://r1'
        )
        self.assertEqual(code, 2, stderr)
        self.assertIn('No such file', stderr)

    def testLoadDriver(self):
        path = self.write('cli_test_driver.py', DRIVER)
        self.addCleanup(self.unload_driver, 'cli_test')
        args = '--load-driver', path, '--use-driver', 'cli_test'
        code, stdout, stderr = self.run_main('-n', '-i', *args, '-e', HELLO, 'dummy://r1')
        self.assertEqual(code, 0, stderr)
        self.assertEqual(
            stdout, f"Searching drivers in {path}...\nDriver 'CliTestDriver' added.\nhello\n"
        )

    def testLoadDriverErrors(self):
        missing = self.path('missing.py')
        code, stdout, stderr = self.run_main(
            '-n', '-i', '--load-driver', missing, '-e', HELLO, 'dummy://r1'
        )
        self.assertEqual(code, 2, stderr)
        self.assertIn('No such file or directory', stderr)

        for name, text, error in (
            ('driver.txt', 'x = 1\n', ImportError),
            ('broken.py', 'x = \n', SyntaxError),
        ):
            path = self.write(name, text)
            stderr = io.StringIO()
            with (
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(stderr),
                self.assertRaises(error),
            ):
                main(['-n', '-i', '--load-driver', path, '-e', HELLO, 'dummy://r1'])
            self.assertEqual(stderr.getvalue(), f'Error in driver {path}\n')

    def testUnknownDriver(self):
        code, stdout, stderr = self.run_main(
            '-n', '-i', '--use-driver', 'bogus', '-e', HELLO, 'dummy://r1'
        )
        self.assertEqual(code, 1)
        self.assertEqual(stderr, 'error: 1 actions failed.\n')

    def testLogdir(self):
        pool = self.write('pool.cfg', POOL)
        logdir = self.path('logs')
        args = '--account-pool', pool, '-l', logdir
        code, stdout, stderr = self.run_main(*args, '-e', HELLO, 'dummy://r1')
        self.assertEqual(code, 0, stderr)
        self.assertEqual(stdout, f'Creating log directory ({logdir})...\nhello\n')
        session = self.read('logs', 'r1.log')
        self.assertIn('User: alice', session)

        # New sessions are appended, unless --overwrite-logs is given.
        self.run_main(*args, '-e', HELLO, 'dummy://r1')
        self.assertEqual(self.read('logs', 'r1.log'), session * 2)
        self.run_main(*args, '--overwrite-logs', '-e', HELLO, 'dummy://r1')
        self.assertLessEqual(len(self.read('logs', 'r1.log')), len(session))

        # --delete-logs deletes the logs of the hosts that succeeded.
        self.run_main(*args, '--delete-logs', '-e', HELLO, 'dummy://r1')
        self.assertEqual(os.listdir(logdir), [])

        # An error is also written to a file of its own.
        code, stdout, stderr = self.run_main(*args, '-e', '{fail "boom"}', 'dummy://r1')
        self.assertEqual(code, 1)
        self.assertEqual(sorted(os.listdir(logdir)), ['r1.log', 'r1.log.error'])
        self.assertIn('boom', self.read('logs', 'r1.log.error'))

    def testLogdirError(self):
        logdir = os.path.join(self.write('file', ''), 'logs')
        code, stdout, stderr = self.run_main('-n', '-i', '-l', logdir, '-e', HELLO, 'dummy://r1')
        self.assertEqual(code, 2, stderr)
        self.assertEqual(stdout, f'Creating log directory ({logdir})...\n')

    def testSleep(self):
        code, stdout, stderr = self.run_main(
            '-n', '-i', '--sleep', '0.001', '-e', HELLO, 'dummy://r1'
        )
        self.assertEqual(code, 0, stderr)
        self.assertEqual(
            stdout, 'Waiting for 0.001 seconds...time expired, starting script.\nhello\n'
        )

    def testInvalidSleep(self):
        code, stdout, stderr = self.run_main('--sleep', 'tomorrow', 'dummy://r1')
        self.assertEqual(code, 2)
        self.assertIn("argument --sleep: invalid duration value: 'tomorrow'", stderr)

    def testFailures(self):
        # -i without an account: the login fails.
        code, stdout, stderr = self.run_main('-i', '-e', HELLO, 'dummy://r1')
        self.assertEqual(code, 1)
        self.assertEqual(stderr, 'error: 1 actions failed.\n')

        code, stdout, stderr = self.run_main(
            '-n', '-i', '-e', '{fail "boom"}', 'dummy://r1', 'dummy://r2'
        )
        self.assertEqual(code, 1)
        self.assertEqual(stderr, 'error: 2 actions failed.\n')

    def testRetry(self):
        script = '{sys.message("attempt")}{fail "boom"}'
        code, stdout, stderr = self.run_main('-n', '-i', '--retry', '1', '-e', script, 'dummy://r1')
        self.assertEqual(code, 1)
        self.assertEqual(stdout, 'attempt\nattempt\n')

    def testExitOnSigint(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with (
            mock.patch('os._exit') as exit,
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            _exit_on_sigint(signal.SIGINT, None)
        exit.assert_called_once_with(130)
        self.assertEqual(stderr.getvalue(), 'Interrupted.\n')

    def testImportOfMainModule(self):
        # The API reference imports Exscript.__main__, which must not run the command.
        with mock.patch('Exscript.cli.main') as main:
            runpy.run_module('Exscript.__main__', run_name='Exscript.__main__')
        main.assert_not_called()

    def testDuration(self):
        self.assertEqual(_duration(''), 0)
        self.assertEqual(_duration('90'), 90)
        self.assertEqual(_duration('1.5m'), 90)
        self.assertEqual(_duration('1h 30m'), 5400)
        self.assertEqual(_duration('2d'), 172800)
        for invalid in 'tomorrow', '1x', '-1', '1; rm -rf ~':
            self.assertRaises(ValueError, _duration, invalid)

    def testPromptValuesAreLiteralsOnly(self):
        cases = {
            '[1, 2]': [1, 2],
            '42': 42,
            'plain text': 'plain text',
            '__import__("os").getcwd()': '__import__("os").getcwd()',
        }
        for typed, expected in cases.items():
            with mock.patch('builtins.input', return_value=typed):
                self.assertEqual(_expand_bracket('count', '{#count}'), expected)

    def testOtp(self):
        stdout = io.StringIO()
        with (
            mock.patch('getpass.getpass', return_value='password') as getpass,
            contextlib.redirect_stdout(stdout),
        ):
            self.assertEqual(otp_main(['9999', 'abc123']), 0)
        getpass.assert_called_once_with('Password: ')
        self.assertEqual(stdout.getvalue(), otp('password', 'abc123', 9999) + '\n')
        self.assertEqual(stdout.getvalue(), 'ACTA AMMO CAR WEB BIN YAP\n')

    def testOtpWithoutNumber(self):
        stderr = io.StringIO()
        with (
            mock.patch('getpass.getpass') as getpass,
            contextlib.redirect_stderr(stderr),
            self.assertRaises(SystemExit) as cm,
        ):
            otp_main(['abc', 'abc123'])
        self.assertEqual(cm.exception.code, 2)
        self.assertIn('first argument must be a number', stderr.getvalue())
        getpass.assert_not_called()

    def testOutputOnTerminalsOnly(self):
        rich = _RichOutput if Console else _Output
        cases = (
            (Tty, Tty, {}, rich),
            (io.StringIO, io.StringIO, {}, _Output),
            (Tty, io.StringIO, {}, _Output),
            (io.StringIO, Tty, {}, _Output),
            (Tty, Tty, {'NO_COLOR': '1'}, _Output),
            (Tty, Tty, {'TERM': 'dumb'}, _Output),
            (io.StringIO, io.StringIO, {'FORCE_COLOR': '1'}, rich),  # any file is a terminal
        )
        for stdout, stderr, variables, cls in cases:
            with (
                self.subTest(stdout=stdout, stderr=stderr, environ=variables),
                environ(**variables),
                contextlib.redirect_stdout(stdout()),
                contextlib.redirect_stderr(stderr()),
            ):
                self.assertIs(type(_create_output()), cls)

    def testPlainOutputWithoutRich(self):
        # rich takes any output for a terminal, but it is not installed.
        path = self.write('hosts.txt', '')
        with environ(FORCE_COLOR='1'), mock.patch.dict(sys.modules, {'rich.console': None}):
            self.assertIs(type(_create_output()), _Output)
            code, stdout, stderr = self.run_main(
                '-n', '-i', '-c', '2', '--hosts', path, '-e', '{fail "boom"}', 'dummy://r1'
            )
        self.assertEqual(code, 1)
        self.assertEqual(stdout, f'Warning: {path} is empty.\n')
        self.assertEqual(stderr, 'error: 1 actions failed.\n')

    def testPlainOutputWithoutTerminal(self):
        path = self.write('hosts.txt', '')
        with environ():
            code, stdout, stderr = self.run_main(
                '-n', '-i', '-c', '2', '--hosts', path, '-e', '{fail "boom"}', 'dummy://r1'
            )
        self.assertEqual(code, 1)
        self.assertEqual(stdout, f'Warning: {path} is empty.\n')
        self.assertEqual(stderr, 'error: 1 actions failed.\n')

    def testLibraryDoesNotImportRich(self):
        # Applications that use the library do not need rich; only the commands use it.
        script = textwrap.dedent('''
            import importlib, pkgutil, sys
            import Exscript
            for module in pkgutil.walk_packages(Exscript.__path__, 'Exscript.'):
                if module.name not in ('Exscript.cli', 'Exscript.__main__'):
                    importlib.import_module(module.name)
            print(sorted(name for name in sys.modules if name.split('.')[0] == 'rich'))
        ''')
        proc = subprocess.run(  # noqa: S603 - runs Python with a fixed script
            [sys.executable, '-c', script], capture_output=True, encoding='utf-8', timeout=60
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, '[]\n')

    @requires_rich
    def testRichMessages(self):
        output, stdout, stderr = self.rich_output()
        hosts = self.write('hosts.txt', '')
        pool = self.write('pool.cfg', '[account-pool]\n')
        args = '--hosts', hosts, '--account-pool', pool, '-e', '{fail "boom"}', 'dummy://r1'
        code, out, err = self.run_main('-n', '-i', *args)
        self.assertEqual(code, 1)
        self.assertEqual((out, err), ('', ''))
        self.assertEqual(
            stdout.getvalue(),
            f'{YELLOW}Warning: {hosts} is empty.{RESET}\n'
            f'{YELLOW}WARNING: No accounts found in account pool file ({pool})!{RESET}\n',
        )
        # One connection: no progress display, and the errors of the queue are red, too.
        self.assertEqual(
            stderr.getvalue(),
            f'{RED}r1 error: boom{RESET}\n'
            f'{RED}r1 finally failed.{RESET}\n'
            f'{RED}error: 1 actions failed.{RESET}\n',
        )

    @requires_rich
    def testRichDriverError(self):
        output, stdout, stderr = self.rich_output()
        path = self.write('broken.py', 'x = \n')
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SyntaxError):
            main(['-n', '-i', '--load-driver', path, '-e', HELLO, 'dummy://r1'])
        self.assertEqual(stderr.getvalue(), f'{RED}Error in driver {path}{RESET}\n')

    @requires_rich
    def testRichProgress(self):
        output, stdout, stderr = self.rich_output()
        script = '{sys.message(__hostname__)}{fail "boom" if __hostname__ is "r2"}'
        code, out, err = self.run_main(
            '-n', '-i', '-c', '2', '-e', script, 'dummy://r1', 'dummy://r2'
        )
        self.assertEqual(code, 1)
        self.assertEqual((out, err, stdout.getvalue()), ('', '', ''))
        # Above the display, the output of the template and a line for each host; the
        # connections run in parallel, so in any order.
        lines = [line.rstrip() for line in shown(stderr.getvalue()).splitlines()]
        expected = ['r1', 'r1 succeeded.', 'r2', 'r2 error: boom', 'r2 finally failed.']
        self.assertCountEqual(lines[:-2], expected)
        self.assertEqual(lines[-2:], ['━' * 40 + ' 2/2 hosts 1 failed', 'error: 1 actions failed.'])
        self.assertIn(f'{GREEN}r1 succeeded.{RESET}\n', stderr.getvalue())
        self.assertIn(f'{RED}r2 finally failed.{RESET}\n', stderr.getvalue())

    @requires_rich
    def testRichProgressShowsRunningJobs(self):
        # The events of the queue as two jobs run: r1 succeeds, r2 fails twice.
        output, stdout, stderr = self.rich_output()
        queue = output.queue(domain='', host_driver=None, verbose=1, max_threads=2)
        self.addCleanup(queue.destroy)
        events = queue.workqueue
        r1, r2 = Thread(None, None, 'r1', {}), Thread(None, None, 'r2', {})  # attempts of jobs
        error = FailException, FailException('boom'), ''
        queue.total = 2

        def display():
            """Returns the words of the display after the bar."""
            return shown(stderr.getvalue()).rsplit('\n', 1)[-1].split()[1:]

        with output.progress():
            self.assertEqual(display(), ['0/2', 'hosts'])
            events.job_started_event(r1)
            events.job_started_event(r2)
            self.assertEqual(display(), ['0/2', 'hosts', 'r1,', 'r2'])
            events.job_succeeded_event(r1)
            self.assertEqual(display(), ['1/2', 'hosts', 'r2'])
            events.job_error_event(r2, error)
            self.assertEqual(display(), ['1/2', 'hosts'])
            events.job_started_event(r2)
            self.assertEqual(display(), ['1/2', 'hosts', 'r2'])
            events.job_error_event(r2, error)
            events.job_aborted_event(r2)
            self.assertEqual(display(), ['2/2', 'hosts', '1', 'failed'])
        lines = [line.rstrip() for line in shown(stderr.getvalue()).splitlines()]
        expected = ['r1 succeeded.', 'r2 error: boom', 'r2 error: boom', 'r2 finally failed.']
        self.assertEqual(lines, [*expected, '━' * 40 + ' 2/2 hosts 1 failed'])
        # The styles of the lines above stay out of the display, which replaces the status bar.
        self.assertNotIn(f'{GREEN}hosts', stderr.getvalue())
        self.assertNotIn(f'{RED}hosts', stderr.getvalue())
        self.assertIs(queue.channel_map['status_bar'], queue.devnull)

    @requires_rich
    def testRichDebugOutputWithoutProgress(self):
        # From verbosity 2 on, the queue logs debug messages, so it keeps its status bar.
        output, stdout, stderr = self.rich_output()
        args = '-n', '-i', '-c', '2', '-v', '2', '-e', '{fail "boom"}', 'dummy://r1'
        code, out, err = self.run_main(*args)
        self.assertEqual(code, 1)
        self.assertNotIn('━', stderr.getvalue())
        self.assertTrue(stderr.getvalue().startswith(f'{RED}r1 error: boom{RESET}\n'))
        self.assertTrue(stderr.getvalue().endswith(f'{RED}error: 1 actions failed.{RESET}\n'))

    @requires_rich
    def testRichInterrupted(self):
        # Without a progress display, e.g. with one connection.
        output, stdout, stderr = self.rich_output()
        with mock.patch('os._exit') as exit:
            _exit_on_sigint(signal.SIGINT, None, output=output)
        exit.assert_called_once_with(130)
        self.assertEqual(stderr.getvalue(), f'{YELLOW}Interrupted.{RESET}\n')

        # The display stops, shows the cursor again, and keeps its last state.
        output, stdout, stderr = self.rich_output()
        queue = output.queue(domain='', host_driver=None, verbose=1, max_threads=2)
        self.addCleanup(queue.destroy)
        with output.progress(), mock.patch('os._exit') as exit:
            _exit_on_sigint(signal.SIGINT, None, output=output)
        exit.assert_called_once_with(130)
        self.assertTrue(stderr.getvalue().endswith(f'\x1b[?25h{YELLOW}Interrupted.{RESET}\n'))
        self.assertEqual(
            shown(stderr.getvalue()).split(), ['━' * 40, '0/0', 'hosts', 'Interrupted.']
        )

    @requires_rich
    def testRichOtp(self):
        output, stdout, stderr = self.rich_output()
        with mock.patch('getpass.getpass', return_value='password'):
            self.assertEqual(otp_main(['9999', 'abc123']), 0)
        self.assertEqual(stdout.getvalue(), f'{BOLD}ACTA AMMO CAR WEB BIN YAP{RESET}\n')
