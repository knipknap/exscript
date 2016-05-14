from builtins import object
import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from functools import partial
import Exscript.util.decorator
from Exscript.util.impl import get_label
from Exscript import Host, Account
from Exscript.protocols import Protocol
from Exscript.protocols.Exception import LoginFailure
from util.reportTest import FakeJob
from multiprocessing import Value

class FakeConnection(object):
    def __init__(self, os = None):
        self.os            = os
        self.data          = {}
        self.host          = None
        self.logged_in     = False
        self.authenticated = False

    def connect(self, hostname, port):
        self.host = hostname

    def get_host(self):
        return self.host

    def login(self, flush = True):
        self.logged_in     = True
        self.login_flushed = flush

    def authenticate(self, flush = True):
        self.authenticated = True
        self.login_flushed = flush

    def close(self, force):
        self.connected    = False
        self.close_forced = force

    def guess_os(self):
        return self.os

class decoratorTest(unittest.TestCase):
    CORRELATE = Exscript.util.decorator

    def bind_cb(self, job, bound_arg1, bound_arg2, **kwargs):
        self.assert_(isinstance(job, FakeJob))
        self.assertEqual(bound_arg1, 'one')
        self.assertEqual(bound_arg2, 'two')
        self.assertEqual(kwargs.get('three'), 3)
        return 123

    def testBind(self):
        from Exscript.util.decorator import bind
        bound  = bind(self.bind_cb, 'one', 'two', three = 3)
        result = bound(FakeJob())
        self.assert_(result == 123, result)

    def ios_cb(self, job, *args):
        return 'hello ios'

    def junos_cb(self, job, *args):
        return 'hello junos'

    def testOsFunctionMapper(self):
        from Exscript.util.decorator import os_function_mapper
        cb_map = {'ios': self.ios_cb, 'junos': self.junos_cb}
        mapper = os_function_mapper(cb_map)
        job    = FakeJob()
        host   = object()

        # Test with 'ios'.
        conn   = FakeConnection(os = 'ios')
        result = mapper(job, host, conn)
        self.assertEqual(result, 'hello ios')

        # Test with 'junos'.
        conn   = FakeConnection(os = 'junos')
        result = mapper(job, host, conn)
        self.assertEqual(result, 'hello junos')

        # Test with unsupported OS.
        conn = FakeConnection(os = 'unknown')
        self.assertRaises(Exception, mapper, job, host, conn)

    def autologin_cb(self, job, host, conn, *args, **kwargs):
        self.assertEqual(conn.logged_in, True)
        self.assertEqual(conn.login_flushed, False)
        return self.bind_cb(job, *args, **kwargs)

    def testAutologin(self):
        from Exscript.util.decorator import autologin
        job  = FakeJob()
        host = job.data['host']
        conn = job.data['conn'] = FakeConnection()

        # Test simple login.
        decor  = autologin(flush = False)
        bound  = decor(self.autologin_cb)
        result = bound(job, host, conn, 'one', 'two', three = 3)
        self.assertEqual(result, 123)

        # Monkey patch the fake connection such that the login fails.
        conn = FakeConnection()
        data = Value('i', 0)
        def fail(data, *args, **kwargs):
            data.value += 1
            raise LoginFailure('intended login failure')
        conn.login = partial(fail, data)

        # Test retry functionality.
        decor = autologin(flush = False, attempts = 5)
        bound = decor(self.autologin_cb)
        job   = FakeJob()
        job.data['conn'] = conn
        self.assertRaises(LoginFailure,
                          bound,
                          job,
                          host,
                          conn,
                          'one',
                          'two',
                          three = 3)
        self.assertEqual(data.value, 5)

    def autoauthenticate_cb(self, job, host, conn, *args, **kwargs):
        self.assertEqual(conn.authenticated, True)
        self.assertEqual(conn.login_flushed, False)
        return self.bind_cb(job, *args, **kwargs)

    def testAutoauthenticate(self):
        from Exscript.util.decorator import autoauthenticate
        job  = FakeJob()
        host = job.data['host']
        conn = job.data['conn'] = FakeConnection()

        # Test simple authentication.
        decor  = autoauthenticate(flush = False)
        bound  = decor(self.autoauthenticate_cb)
        result = bound(job, host, conn, 'one', 'two', three = 3)
        self.assertEqual(result, 123)

        # Monkey patch the fake connection such that the login fails.
        conn = FakeConnection()
        data = Value('i', 0)
        def fail(data, *args, **kwargs):
            data.value += 1
            raise LoginFailure('intended login failure')
        conn.authenticate = partial(fail, data)

        # Test retry functionality.
        decor = autoauthenticate(flush = False, attempts = 5)
        bound = decor(self.autoauthenticate_cb)
        job   = FakeJob()
        job.data['conn'] = conn
        self.assertRaises(LoginFailure,
                          bound,
                          job,
                          host,
                          conn,
                          'one',
                          'two',
                          three = 3)
        self.assertEqual(data.value, 5)

    def testDeprecated(self):
        pass #not really needed.

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(decoratorTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
