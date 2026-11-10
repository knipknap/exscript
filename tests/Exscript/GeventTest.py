"""Exscript under gevent: the application patches the standard library, and the queue works."""

import importlib.util
import os
import subprocess
import sys
import unittest

SCRIPT = '''
from gevent import monkey

monkey.patch_all()

import sys

from Exscript import Account, Host, PrivateKey, Queue
from Exscript.emulators import VirtualDevice
from Exscript.servers import SSHd, Telnetd

key = PrivateKey.from_file(sys.argv[1])
servers, hosts = [], []
for i in range(5):
    for scheme, cls, kwargs in ('telnet', Telnetd, {}), ('ssh', SSHd, {'key': key}):
        device = VirtualDevice('r%d' % i, login_type=VirtualDevice.LOGIN_TYPE_NONE, strict=False)
        device.add_command('show version', 'test device ' + scheme)
        server = cls('127.0.0.1', 0, device, **kwargs)
        server.timeout = 0.05
        server.start()
        servers.append(server)
        host = Host('%s://127.0.0.1:%d' % (scheme, server.port))
        host.set_option('connect_rate_limit', 0)
        host.set_option('verify_fingerprint', False)
        host.set_option('driver', 'generic')
        hosts.append(host)

responses = []


def run(job, host, conn):
    conn.protocol_authenticate(Account('user', 'password', needs_lock=False))
    conn.expect_prompt()
    conn.execute('show version')
    responses.append(conn.response)


queue = Queue(verbose=0, max_threads=len(hosts))
queue.run(hosts, run)
queue.shutdown()
for server in servers:
    server.exit()
    server.join()
print(sorted(r.strip().splitlines()[-1] for r in responses))
'''


@unittest.skipUnless(importlib.util.find_spec('gevent'), 'gevent is not installed')
class GeventTest(unittest.TestCase):
    def testQueue(self):
        # The queue hangs if it waits on a lock that gevent does not patch.
        keyfile = os.path.join(os.path.dirname(__file__), 'protocols', 'id_rsa')
        result = subprocess.run(  # noqa: S603 (this interpreter with a constant script)
            [sys.executable, '-W', 'ignore', '-c', SCRIPT, keyfile],
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = ['test device ssh'] * 5 + ['test device telnet'] * 5
        self.assertEqual(result.stdout.strip(), repr(expected))


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(GeventTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
