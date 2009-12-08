import sys, unittest, re, os.path, threading, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from Exscript.workqueue import Action

class TestAction(Action):
    id = 0

    def __init__(self):
        self.__class__.id += 1
        Action.__init__(self, name = "action %s" % self.__class__.id)

    def execute(self, lock, global_ctx, local_ctx):
        lock.acquire()
        if not global_ctx.has_key('sum'):
            global_ctx['sum'] = 0
        if not global_ctx.has_key('randsum'):
            global_ctx['randsum'] = 0
        global_ctx['sum'] += 1
        lock.release()
        for number in range(random.randint(0, 4567)):
            lock.acquire()
            global_ctx['randsum'] += number
            lock.release()
        return True

class ActionTest(unittest.TestCase):
    def setUp(self):
        pass

    def testExecute(self):
        global_ctx = {'sum': 0, 'randsum': 0}

        action = Action(name = 'test', debug = 1)
        self.assert_(action.name  == 'test')
        self.assert_(action.debug == 1)
        self.assertRaises(Exception, action.execute)

        action = TestAction()
        self.assert_(action.name  == 'action 1', action.name)
        self.assert_(action.debug == 0)
        action.execute(threading.Lock(), global_ctx, {})

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(ActionTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
