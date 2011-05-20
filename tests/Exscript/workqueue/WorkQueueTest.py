import sys, unittest, re, os.path, threading, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from Exscript.workqueue import WorkQueue, Action, Sequence
from ActionTest         import TestAction

class WorkQueueTest(unittest.TestCase):
    CORRELATE = WorkQueue

    def setUp(self):
        self.wq = WorkQueue()

    def testConstructor(self):
        self.assertEqual(1, self.wq.get_max_threads())
        self.assertEqual(0, self.wq.debug)

    def testSetDebug(self):
        self.assertEqual(0, self.wq.debug)
        self.wq.set_debug(2)
        self.assertEqual(2, self.wq.debug)

    def testGetMaxThreads(self):
        self.assertEqual(1, self.wq.get_max_threads())
        self.wq.set_max_threads(9)
        self.assertEqual(9, self.wq.get_max_threads())

    def testSetMaxThreads(self):
        self.testGetMaxThreads()

    def testEnqueue(self):
        self.assertEqual(0, self.wq.get_length())
        self.wq.enqueue(Action())
        self.assertEqual(1, self.wq.get_length())
        self.wq.enqueue(Action())
        self.assertEqual(2, self.wq.get_length())
        self.wq.shutdown(True)
        self.assertEqual(0, self.wq.get_length())

        # Enqueue 111 * 3 = 333 actions.
        lock = threading.Lock()
        data = {}
        for i in range(111):
            actions  = [TestAction(lock, data),
                        TestAction(lock, data),
                        TestAction(lock, data)]
            sequence = Sequence(actions = actions)
            self.wq.enqueue(sequence)
        self.assertEqual(111, self.wq.get_length())

        # Run them, using 50 threads in parallel.
        self.wq.set_max_threads(50)
        self.wq.unpause()
        self.wq.wait_until_done()
        self.wq.pause()

        # Check whether each has run successfully.
        self.assertEqual(0,   self.wq.get_length())
        self.assertEqual(333, data['sum'])
        self.wq.shutdown()
        self.assertEqual(0, self.wq.get_length())

    def testEnqueueOrIgnore(self):
        self.assertEqual(0, self.wq.get_length())
        self.wq.enqueue_or_ignore(Action(name = 'one'))
        self.assertEqual(1, self.wq.get_length())
        self.wq.enqueue_or_ignore(Action(name = 'two'))
        self.assertEqual(2, self.wq.get_length())
        self.wq.enqueue_or_ignore(Action(name = 'one'))
        self.assertEqual(2, self.wq.get_length())
        self.wq.shutdown(True)
        self.assertEqual(0, self.wq.get_length())

        # Stress testing from testEnqueue() not repeated here.

    def testPriorityEnqueue(self):
        # Well, this test sucks.
        self.assertEqual(0, self.wq.get_length())
        self.wq.priority_enqueue(Action())
        self.assertEqual(1, self.wq.get_length())
        self.wq.priority_enqueue(Action())
        self.assertEqual(2, self.wq.get_length())

    def testPriorityEnqueueOrRaise(self):
        action1 = Action(name = 'foo')
        action2 = Action(name = 'bar')
        action3 = Action(name = 'foo')
        self.assertEqual(0, self.wq.get_length())

        self.wq.priority_enqueue_or_raise(action1)
        self.assertEqual(1, self.wq.get_length())
        self.wq.priority_enqueue_or_raise(action2)
        self.assertEqual(2, self.wq.get_length())
        self.wq.priority_enqueue_or_raise(action3)
        self.assertEqual(2, self.wq.get_length())

    def testPause(self):
        pass # See testEnqueue()

    def testWaitFor(self):
        actions = [Action(), Action(), Action(), Action()]
        for action in actions:
            self.wq.enqueue(action)
        self.assertEqual(4, self.wq.get_length())
        self.wq.unpause()

        # Test that wait_for accepts an action hash.
        self.wq.wait_for(actions[0].__hash__())
        self.assert_(self.wq.get_length() < 4)

        # Test whether it accepts an action object.
        for action in actions:
            self.wq.wait_for(action)
        self.assertEqual(0, self.wq.get_length())

    def testWaitForActivity(self):
        action1 = Action()
        action2 = Action()
        action3 = Action()
        self.wq.enqueue(action1)
        self.wq.enqueue(action2)
        self.wq.enqueue(action3)
        self.wq.unpause()
        while not self.wq.get_length() == 0:
            self.wq.wait_for_activity()
        self.assertEqual(0, self.wq.get_length())

    def testUnpause(self):
        pass # See testEnqueue()

    def testWaitUntilDone(self):
        pass # See testEnqueue()

    def testShutdown(self):
        pass # See testEnqueue()

    def testIsPaused(self):
        self.assert_(self.wq.is_paused())
        self.wq.pause()
        self.assert_(self.wq.is_paused())
        self.wq.unpause()
        self.failIf(self.wq.is_paused())
        self.wq.pause()
        self.assert_(self.wq.is_paused())

    def testInQueue(self):
        action1 = Action()
        action2 = Action()
        self.failIf(self.wq.in_queue(action1))
        self.failIf(self.wq.in_queue(action2))

        self.wq.enqueue(action1)
        self.assert_(self.wq.in_queue(action1))
        self.failIf(self.wq.in_queue(action2))

        self.wq.enqueue(action2)
        self.assert_(self.wq.in_queue(action1))
        self.assert_(self.wq.in_queue(action2))

        self.wq.shutdown()
        self.failIf(self.wq.in_queue(action1))
        self.failIf(self.wq.in_queue(action2))

    def testInProgress(self):
        this = self
        class TestAction(Action):
            def execute():
                this.assert_(this.wq.in_progress(self))
        action = TestAction()
        self.wq.enqueue(action)
        self.wq.shutdown()
        this.failIf(self.wq.in_progress(action))

    def testGetRunningActions(self):
        this = self
        class TestAction(Action):
            def execute():
                this.assertEqual(this.wq.get_running_actions(), [self])
        action = TestAction()
        self.assertEqual(self.wq.get_running_actions(), [])
        self.wq.enqueue(action)
        self.wq.shutdown(True)
        self.assertEqual(self.wq.get_running_actions(), [])

    def testGetLength(self):
        pass # See testEnqueue()

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(WorkQueueTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
