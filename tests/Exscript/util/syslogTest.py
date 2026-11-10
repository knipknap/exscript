import os
import socket
import sys
import unittest

import Exscript.util.syslog
from Exscript.util.syslog import netlog


class syslogTest(unittest.TestCase):
    CORRELATE = Exscript.util.syslog

    def setUp(self):
        # IPv6 first: WSL's consomme networking loses datagrams sent with sendto() to 127.0.0.1.
        for family, self.host in (socket.AF_INET6, '::1'), (socket.AF_INET, '127.0.0.1'):
            self.server = socket.socket(family, socket.SOCK_DGRAM)
            self.addCleanup(self.server.close)
            try:
                self.server.bind((self.host, 0))
                break
            except OSError:  # no IPv6 on this host
                continue
        self.server.settimeout(5)
        self.port = self.server.getsockname()[1]

    def testNetlog(self):
        netlog('hellö', source='router1', host=self.host, port=self.port)
        self.assertEqual(self.server.recv(1024), '<15>router1: hellö'.encode())  # user.debug

        netlog('x', source='s', host=self.host, port=self.port, priority=3, facility=4 << 3)
        self.assertEqual(self.server.recv(1024), b'<35>s: x')  # auth.err

    def testDefaultSource(self):
        netlog('x', host=self.host, port=self.port)
        expected = '<15>%s[%d]: x' % (sys.argv[0], os.getpid())
        self.assertEqual(self.server.recv(1024), expected.encode())
