import os
import socket
import sys
import unittest

import Exscript.util.syslog
from Exscript.util.syslog import netlog


class syslogTest(unittest.TestCase):
    CORRELATE = Exscript.util.syslog

    def setUp(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server.bind(('127.0.0.1', 0))
        self.server.settimeout(5)
        self.addCleanup(self.server.close)
        self.port = self.server.getsockname()[1]

    def testNetlog(self):
        netlog('hellö', source='router1', host='127.0.0.1', port=self.port)
        self.assertEqual(self.server.recv(1024), '<15>router1: hellö'.encode())  # user.debug

        netlog('x', source='s', host='127.0.0.1', port=self.port, priority=3, facility=4 << 3)
        self.assertEqual(self.server.recv(1024), b'<35>s: x')  # auth.err

    def testDefaultSource(self):
        netlog('x', host='127.0.0.1', port=self.port)
        expected = '<15>%s[%d]: x' % (sys.argv[0], os.getpid())
        self.assertEqual(self.server.recv(1024), expected.encode())
