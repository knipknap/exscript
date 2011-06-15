import sys, unittest, re, os.path, threading, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

import time
from threading import Thread
from multiprocessing import Value
from Exscript.workqueue import Pipeline

class PipelineTest(unittest.TestCase):
    CORRELATE = Pipeline

    def setUp(self):
        self.pipeline = Pipeline()

    def testConstructor(self):
        self.assertEqual(self.pipeline.get_max_working(), 1)
        pipeline = Pipeline(max_working = 10)
        self.assertEqual(pipeline.get_max_working(), 10)

    def testLen(self):
        self.assertEqual(len(self.pipeline), 0)

    def testContains(self):
        item1 = object()
        item2 = object()
        self.assert_(item1 not in self.pipeline)
        self.assert_(item2 not in self.pipeline)

        self.pipeline.append(item1)
        self.assert_(item1 in self.pipeline)
        self.assert_(item2 not in self.pipeline)

        self.pipeline.append(item2)
        self.assert_(item1 in self.pipeline)
        self.assert_(item2 in self.pipeline)

    def testFind(self):
        item1       = object()
        item2       = object()
        find_none   = lambda x: False
        find_all    = lambda x: True
        find_second = lambda x: x == item2
        self.assertEqual(self.pipeline.find(find_none), None)
        self.assertEqual(self.pipeline.find(find_all), None)
        self.assertEqual(self.pipeline.find(find_second), None)

        self.pipeline.append(item1)
        self.pipeline.append(item2)
        self.assertEqual(self.pipeline.find(find_none), None)
        self.assertEqual(self.pipeline.find(find_all), item1)
        self.assertEqual(self.pipeline.find(find_second), item2)

    def testHasId(self):
        item1 = object()
        item2 = object()
        self.assertEqual(self.pipeline.has_id(id(item1)), False)
        self.assertEqual(self.pipeline.has_id(id(item2)), False)

        self.pipeline.append(item1)
        self.assertEqual(self.pipeline.has_id(id(item1)), True)
        self.assertEqual(self.pipeline.has_id(id(item2)), False)

        self.pipeline.append(item2)
        self.assertEqual(self.pipeline.has_id(id(item1)), True)
        self.assertEqual(self.pipeline.has_id(id(item2)), True)

    def testTaskDone(self):
        self.testNext()

    def testAppend(self):
        self.testContains()

    def testAppendleft(self):
        item1      = object()
        item2      = object()
        item3      = object()
        item4      = object()
        find_first = lambda x: True
        self.assertEqual(self.pipeline.find(find_first), None)

        self.pipeline.append(item1)
        self.pipeline.append(item2)
        self.assertEqual(self.pipeline.find(find_first), item1)

        self.pipeline.appendleft(item3)
        self.assertEqual(self.pipeline.find(find_first), item3)

        self.pipeline.appendleft(item4, True)
        self.assertEqual(self.pipeline.find(find_first), item4)

    def testPrioritize(self):
        item1      = object()
        item2      = object()
        find_first = lambda x: True
        self.assertEqual(self.pipeline.find(find_first), None)

        self.pipeline.append(item1)
        self.pipeline.append(item2)
        self.assertEqual(self.pipeline.find(find_first), item1)

        self.pipeline.prioritize(item2)
        self.assertEqual(self.pipeline.find(find_first), item2)
        self.pipeline.prioritize(item2)
        self.assertEqual(self.pipeline.find(find_first), item2)

        self.pipeline.prioritize(item1, True)
        self.assertEqual(self.pipeline.find(find_first), item1)
        self.pipeline.prioritize(item1, True)
        self.assertEqual(self.pipeline.find(find_first), item1)

    def testClear(self):
        self.testAppendleft()
        self.assertEqual(len(self.pipeline), 4)
        self.pipeline.clear()
        self.assertEqual(len(self.pipeline), 0)

    def testStop(self):
        self.assertEqual(self.pipeline.get_max_working(), 1)
        item1 = object()
        item2 = object()
        self.pipeline.append(item1)
        self.pipeline.append(item2)
        self.assertEqual(len(self.pipeline), 2)

        thread_completed = Value('i', 0)
        class deadlock_until_stop(Thread):
            def run(inner_self):
                self.assertEqual(self.pipeline.next(), item1)
                self.assertEqual(self.pipeline.next(), None) # ***
                thread_completed.value = 1

        thread = deadlock_until_stop()
        thread.daemon = True
        thread.start()

        time.sleep(0.5) # Hack: Wait until the thread has reached "***"

        self.assertEqual(thread_completed.value, 0)
        self.pipeline.stop()
        thread.join()
        self.assertEqual(thread_completed.value, 1)

    def testPause(self):
        item1 = object()
        self.pipeline.append(item1)
        self.pipeline.pause()

        class complete_all(Thread):
            def run(inner_self):
                while True:
                    task = self.pipeline.next()
                    if task is None:
                        break
                    self.pipeline.task_done(task)

        thread = complete_all()
        thread.daemon = True
        thread.start()

        time.sleep(.2) # hack: wait long enough for the task to complete.
        self.assertEqual(len(self.pipeline), 1) # should not be completed.
        self.pipeline.unpause()
        self.pipeline.wait_all() # now it should not deadlock.

    def testUnpause(self):
        self.testPause()

    def testSleep(self):
        self.assertEqual(self.pipeline.get_max_working(), 1)
        item1 = object()
        item2 = object()
        self.pipeline.append(item1)
        self.pipeline.append(item2)
        self.assertEqual(len(self.pipeline), 2)

        self.assertEqual(self.pipeline.next(), item1)
        self.assertEqual(len(self.pipeline), 2)
        self.pipeline.sleep(item1)
        self.assertEqual(len(self.pipeline), 2)

        # This would normally deadlock if the job were not sleeping,
        # because we have reached the max_working threshold.
        self.assertEqual(self.pipeline.next(), item2)
        self.assertEqual(len(self.pipeline), 2)

        self.pipeline.wake(item1)
        self.assertRaises(Exception, self.pipeline.wake, item2)
        self.assertEqual(len(self.pipeline), 2)

    def testWake(self):
        self.testSleep()

    def testWaitForId(self):
        item1 = object()
        item2 = object()
        self.pipeline.append(item1)
        self.pipeline.append(item2)

        item = self.pipeline.next()
        class complete_item(Thread):
            def run(inner_self):
                time.sleep(.1)
                self.pipeline.task_done(item)
        thread = complete_item()
        thread.daemon = True
        thread.start()

        self.assertEqual(len(self.pipeline), 2)
        self.pipeline.wait_for_id(id(item)) # Must not deadlock.
        self.assertEqual(len(self.pipeline), 1)

    def testWait(self):
        item1 = object()
        item2 = object()
        self.pipeline.append(item1)
        self.pipeline.append(item2)

        self.assertEqual(len(self.pipeline), 2)
        self.pipeline.wait()
        self.assertEqual(len(self.pipeline), 2)

        item = self.pipeline.next()
        class complete_item(Thread):
            def run(inner_self):
                time.sleep(.1)
                self.pipeline.task_done(item)
        thread = complete_item()
        thread.daemon = True
        thread.start()

        self.pipeline.wait() # Must not deadlock.
        self.assertEqual(len(self.pipeline), 1)

    def testWaitAll(self):
        item1 = object()
        item2 = object()
        self.pipeline.append(item1)
        self.pipeline.append(item2)

        class complete_all(Thread):
            def run(inner_self):
                while True:
                    task = self.pipeline.next()
                    if task is None:
                        break
                    self.pipeline.task_done(task)
        thread = complete_all()
        thread.daemon = True
        thread.start()

        self.pipeline.wait_all() # Must not deadlock.
        self.assertEqual(len(self.pipeline), 0)

    def testWithLock(self):
        result = self.pipeline.with_lock(lambda p, x: x, 'test')
        self.assertEqual(result, 'test')

    def testSetMaxWorking(self):
        self.assertEqual(self.pipeline.get_max_working(), 1)
        self.pipeline.set_max_working(2)
        self.assertEqual(self.pipeline.get_max_working(), 2)

    def testGetMaxWorking(self):
        self.testSetMaxWorking()

    def testGetWorking(self):
        item = object()
        self.pipeline.append(item)
        self.assertEqual(self.pipeline.get_working(), [])
        theitem = self.pipeline.next()
        self.assertEqual(self.pipeline.get_working(), [item])
        self.pipeline.task_done(theitem)

    def testNext(self):
        # Repeat with max_working set to a value larger than the
        # queue length (i.e. no locking).
        self.pipeline.set_max_working(4)
        item1 = object()
        item2 = object()
        item3 = object()
        item4 = object()
        self.pipeline.append(item1)
        self.pipeline.append(item2)
        self.pipeline.appendleft(item3, True)
        self.pipeline.appendleft(item4)

        self.assertEqual(self.pipeline.next(), item3)
        self.assertEqual(self.pipeline.next(), item4)
        self.assertEqual(self.pipeline.next(), item1)
        self.assertEqual(self.pipeline.next(), item2)
        self.assert_(item1 in self.pipeline)
        self.assert_(item2 in self.pipeline)
        self.assert_(item3 in self.pipeline)
        self.assert_(item4 in self.pipeline)
        self.assertEqual(len(self.pipeline), 4)
        self.pipeline.clear()
        self.assertEqual(len(self.pipeline), 0)

        # Repeat with max_working = 2.
        self.pipeline.set_max_working(2)
        self.pipeline.append(item1)
        self.pipeline.append(item2)
        self.pipeline.appendleft(item3, True)
        self.pipeline.appendleft(item4)

        self.assertEqual(self.pipeline.next(), item3)
        self.assertEqual(self.pipeline.next(), item4)
        self.assert_(item3 in self.pipeline)
        self.assert_(item4 in self.pipeline)
        self.pipeline.task_done(item4)
        self.assert_(item4 not in self.pipeline)

        self.assertEqual(self.pipeline.next(), item1)
        self.assert_(item1 in self.pipeline)
        self.pipeline.task_done(item3)
        self.assert_(item3 not in self.pipeline)

        self.assertEqual(self.pipeline.next(), item2)
        self.assert_(item2 in self.pipeline)
        self.pipeline.task_done(item2)
        self.assert_(item2 not in self.pipeline)
        self.pipeline.task_done(item1)
        self.assert_(item1 not in self.pipeline)
        self.assertEqual(len(self.pipeline), 0)

        # Repeat with max_working = 1.
        self.pipeline.set_max_working(1)
        self.pipeline.append(item1)
        self.pipeline.append(item2)
        self.pipeline.appendleft(item3, True)
        self.pipeline.appendleft(item4)

        self.assertEqual(self.pipeline.next(), item3)
        self.assert_(item3 in self.pipeline)
        self.pipeline.task_done(item3)
        self.assert_(item3 not in self.pipeline)

        self.assertEqual(self.pipeline.next(), item4)
        self.assert_(item4 in self.pipeline)
        self.pipeline.task_done(item4)
        self.assert_(item4 not in self.pipeline)

        self.assertEqual(self.pipeline.next(), item1)
        self.assert_(item1 in self.pipeline)
        self.pipeline.task_done(item1)
        self.assert_(item1 not in self.pipeline)

        self.assertEqual(self.pipeline.next(), item2)
        self.assert_(item2 in self.pipeline)
        self.pipeline.task_done(item2)
        self.assert_(item2 not in self.pipeline)
        self.assertEqual(len(self.pipeline), 0)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(PipelineTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
