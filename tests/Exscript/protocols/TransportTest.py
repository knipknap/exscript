import sys, unittest, re, os.path

class TransportTest(unittest.TestCase):
    def testTransport(self, transport_cls):
        transport = transport_cls(echo = 0)
        self.assert_(transport.response is None)
        transport.connect('localhost')
        self.assert_(transport.response is None)

        transport.authenticate('test', 'test', wait = True)
        self.assert_(transport.response is not None)
        self.assert_(len(transport.response) > 0)

        transport.execute('ls')
        self.assert_(transport.response is not None)
        self.assert_(transport.response.startswith('ls'))

        transport.send('exit\r')
        self.assert_(transport.response is not None)
        self.assert_(transport.response.startswith('ls'))

        transport.close()
        self.assert_(transport.response is not None)
        self.assert_(len(transport.response) > 0)
