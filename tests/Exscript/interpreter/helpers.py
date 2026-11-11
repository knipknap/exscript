"""
Helpers for the tests of the template language: a virtual device that records
the commands that it receives, and a test case that runs templates on it.
"""

import re
import unittest

from Exscript.emulators import VirtualDevice
from Exscript.protocols import Dummy
from Exscript.util import template


class RecordingDevice(VirtualDevice):
    """
    A virtual device that needs no login, answers unknown commands with the
    prompt only, and records the commands that it receives.
    """

    def __init__(self, hostname='r1', **kwargs):
        kwargs.setdefault('login_type', VirtualDevice.LOGIN_TYPE_NONE)
        kwargs.setdefault('strict', False)
        super().__init__(hostname, **kwargs)
        self.received = []

    def do(self, command):
        self.received.append(command)
        return super().do(command)


def connect(device, timeout=5):
    """
    Returns a Dummy connection to the given device that has read the banner
    and the first prompt.
    """
    conn = Dummy(device=device, timeout=timeout)
    conn.connect(device.hostname)
    conn.expect_prompt()
    return conn


def split_error(exc):
    """
    Splits the message of an error that the lexer raised with a position
    into the lines of the template that it shows, the line that marks the
    position with carets, and the message below that line.
    """
    lines = str(exc).split('\n')
    for i, line in enumerate(lines):
        if re.fullmatch(r' *\^+', line):
            return lines[1:i], line, '\n'.join(lines[i + 1 :])
    raise AssertionError('The message shows no position: %r' % str(exc))


class TemplateTestCase(unittest.TestCase):
    """
    Runs templates on a RecordingDevice that knows the commands
    "show version" and "ls".
    """

    def setUp(self):
        self.device = RecordingDevice()
        self.device.add_command('show version', 'Version 1.0\nUptime 5 days')
        self.device.add_command('ls', 'file1\nfile2')
        self.conn = connect(self.device)
        self.addCleanup(self.conn.close, force=True)

    def evaluate(self, text, **kwargs):
        """
        Runs the template with template.eval() and returns its variables.
        """
        return template.eval(self.conn, text, **kwargs)

    def assertSent(self, *commands):
        """
        Checks that the device received the given commands, each with a CR.
        """
        self.assertEqual(self.device.received, [command + '\r' for command in commands])

    def assertError(self, exc, lines, marker, message):
        """
        Checks the lines of the template, the position marker and the message
        that the given error shows.
        """
        self.assertEqual(split_error(exc), (lines, marker, message))
