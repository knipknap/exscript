import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

import Exscript.util.decorator
from Exscript import Host
from Exscript.protocols.Exception import LoginFailure
from util.reportTest import FakeJob

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
        self.assert_(isinstance(conn, FakeConnection))
        self.assert_(bound_arg1 == 'one', bound_arg1)
        self.assert_(bound_arg2 == 'two', bound_arg2)
        self.assert_(kwargs.get('three') == 3, kwargs.get('three'))
        return 123

    def testBind(self):
        from Exscript.util.decorator import bind
        bound  = bind(self.bind_cb, 'one', 'two', three = 3)
        result = bound(FakeJob(), Host('foo'), FakeConnection())
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
        bound  = connect(self.connect_cb)
        result = bound(FakeJob(),
                       Host('foo'),
                       FakeConnection(),
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
        bound  = autologin(self.autologin_cb, False)
        result = bound(FakeJob(),
                       Host('dummy://foo'),
                       FakeConnection(),
                       'one',
                       'two',
                       three = 3)
        self.assertEqual(result, 123)

        # Monkey patch the fake connection such that the login fails.
        conn = FakeConnection()
        conn.data = 0
        def fail(*args, **kwargs):
            conn.data += 1
            raise LoginFailure('intended login failure')
        conn.login = fail

        # Test retry functionality.
        bound = autologin(self.autologin_cb, False, attempts = 5)
        job   = FakeJob()
        self.assertRaises(LoginFailure,
                          bound,
                          job,
                          Host('dummy://foo'),
                          conn,
                          'one',
                          'two',
                          three = 3)
        self.assertEqual(conn.data, 5)

    def testDeprecated(self):
        pass #not really needed.

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(decoratorTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
