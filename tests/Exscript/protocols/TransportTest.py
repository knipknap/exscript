import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

class TransportTest(unittest.TestCase):
    """
    Since protocols.Transport is abstract, this test is only a base class
    for other protocols. It does not do anything fancy on its own.
    """
    def testTransport(self):
        from Exscript.protocols.Transport import Transport
        transport = Transport()

    def checkTransport(self, transport_cls):
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

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(TransportTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
