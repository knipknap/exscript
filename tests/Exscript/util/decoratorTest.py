import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from functools import partial
import Exscript.util.decorator
from Exscript import Host, Account
from Exscript.protocols import Protocol
from Exscript.protocols.Exception import LoginFailure
from util.reportTest import FakeJob
from multiprocessing import Value

class FakeConnection(object):
    def __init__(self, os = None):
        self.os   = os
        self.data = {}
        self.host = None

    def connect(self, hostname, port):
        self.host = hostname

    def get_host(self):
        return self.host

    def login(self, flush = True):
        self.logged_in     = True
        self.login_flushed = flush

    def close(self, force):
        self.connected    = False
        self.close_forced = force

    def guess_os(self):
        return self.os

class decoratorTest(unittest.TestCase):
    CORRELATE = Exscript.util.decorator

    def bind_cb(self, job, host, conn, bound_arg1, bound_arg2, **kwargs):
        self.assert_(isinstance(job, FakeJob))
        self.assert_(isinstance(conn, Protocol) or \
                     isinstance(conn, FakeConnection))
        self.assertEqual(bound_arg1, 'one')
        self.assertEqual(bound_arg2, 'two')
        self.assertEqual(kwargs.get('three'), 3)
        return 123

    def testBind(self):
        from Exscript.util.decorator import bind
        bound  = bind(self.bind_cb, 'one', 'two', three = 3)
        result = bound(FakeJob(), Host('dummy://foo'), Protocol())
        self.assert_(result == 123, result)

    def ios_cb(self, job, host, conn):
        return 'hello ios'

    def junos_cb(self, job, host, conn):
        return 'hello junos'

    def testOsFunctionMapper(self):
        from Exscript.util.decorator import os_function_mapper
        cb_map = {'ios': self.ios_cb, 'junos': self.junos_cb}
        result = os_function_mapper(FakeJob(),
                                    Host('dummy://foo'),
                                    FakeConnection(os = 'ios'),
                                    cb_map)
        self.assertEqual(result, 'hello ios')

        result = os_function_mapper(FakeJob(),
                                    Host('dummy://foo'),
                                    FakeConnection(os = 'junos'),
                                    cb_map)
        self.assertEqual(result, 'hello junos')

        self.assertRaises(Exception,
                          os_function_mapper,
                          FakeJob(),
                          Host('foo'),
                          FakeConnection(),
                          cb_map)

    def connect_cb(self, job, host, conn, *args, **kwargs):
        self.assertEqual(conn.get_host(), 'foo')
        return self.bind_cb(job, host, conn, *args, **kwargs)

    def testConnect(self):
        from Exscript.util.decorator import connect
        bound  = connect()(self.connect_cb)
        result = bound(FakeJob(),
                       Host('dummy://foo'),
                       'one',
                       'two',
                       three = 3)
        self.assertEqual(result, 123)

    def autologin_cb(self, job, host, conn, *args, **kwargs):
        self.assertEqual(conn.logged_in, True)
        self.assertEqual(conn.login_flushed, False)
        return self.bind_cb(job, host, conn, *args, **kwargs)

    def testAutologin(self):
        from Exscript.util.decorator import autologin

        # Test simple login.
        decor  = autologin(flush = False)
        bound  = decor(self.autologin_cb)
        result = bound(FakeJob(),
                       Host('dummy://foo'),
                       FakeConnection(),
                       'one',
                       'two',
                       three = 3)
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
        self.assertRaises(LoginFailure,
                          bound,
                          job,
                          Host('dummy://foo'),
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
