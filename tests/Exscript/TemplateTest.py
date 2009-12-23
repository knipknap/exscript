import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from Exscript                import Queue, Account, Logger
from Exscript.util           import template
from Exscript.util.decorator import bind
from Exscript.protocols      import Dummy

test_dir = '../templates'

class Log(object):
    data = ''
    def collect(self, data):
        self.data += data
        return data

def ios_dummy_cb(conn, template_test):
    # Warning: Assertions raised in this function happen in a subprocess!
    log       = Log()
    test_name = conn.get_host().get_address()
    tmpl      = os.path.join(test_dir, test_name, 'test.exscript')
    expected  = os.path.join(test_dir, test_name, 'expected')
    conn.signal_connect('data_received', log.collect)
    conn.open()
    conn.authenticate(wait = True)
    template.eval_file(conn, tmpl, slot = 10)
    #open(expected, 'w').write(log.data)
    if log.data != open(expected).read():
        print
        print "Got:", log.data
        print "---------------------------------------------"
        print "Expected:", open(expected).read()
    template_test.assertEqual(log.data, open(expected).read())

class IOSDummy(Dummy):
    def __init__(self, *args, **kwargs):
        #kwargs['echo'] = True
        Dummy.__init__(self, *args, **kwargs)

    def connect(self, test_name, *args, **kwargs):
        filename = os.path.join(test_dir, test_name, 'pseudodev.py')
        self.load_command_handler_from_file(filename)
        return Dummy.connect(self, test_name, *args, **kwargs)

class TemplateTest(unittest.TestCase):
    def setUp(self):
        account     = Account('sab', '')
        self.queue  = Queue(verbose = 0, max_threads = 1)
        self.logger = Logger(self.queue)
        self.queue.add_protocol('ios', IOSDummy)
        self.queue.add_account(account)

    def tearDown(self):
        self.queue.shutdown()

    def testTemplates(self):
        callback = bind(ios_dummy_cb, self)
        for test in os.listdir(test_dir):
            self.queue.run('ios:' + test, callback)
        self.queue.shutdown()

        # Unfortunately, unittest.TestCase does not fail if self.assert()
        # was called from a subthread, so this is our workaround...
        failed = self.logger.get_error_actions()
        self.assert_(not failed)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(TemplateTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
