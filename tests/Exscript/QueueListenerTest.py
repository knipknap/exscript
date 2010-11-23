import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from Exscript.QueueListener import QueueListener
from util.reportTest        import FakeQueue

class QueueListenerTest(unittest.TestCase):
    CORRELATE = QueueListener

    def setUp(self):
        self.listener = QueueListener(FakeQueue())

    def testConstructor(self):
        pass # See setUp()

    def testActionEnqueued(self):
        self.assertRaises(Exception, self.listener._action_enqueued, object)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(QueueListenerTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
