import os
import tempfile
import unittest

import Exscript.util.log
from Exscript import Account, Host, Logger, Queue
from Exscript.util.decorator import autologin
from Exscript.util.log import log_to, log_to_file


class logTest(unittest.TestCase):
    CORRELATE = Exscript.util.log

    def runQueue(self, function, hosts):
        queue = Queue(verbose=0, max_threads=1)
        self.addCleanup(queue.destroy)
        queue.add_account(Account('admin', 'secret'))
        queue.run(hosts, autologin()(function))
        queue.shutdown()

    def testLogTo(self):
        # The decorator labels the function, and the queue logs each host.
        logger = Logger()

        def show_version(job, host, conn):
            conn.execute('show version')

        self.assertIs(log_to(logger)(show_version), show_version)
        self.runQueue(show_version, [Host('dummy://r1'), Host('dummy://r2')])
        logs = sorted(logger.get_succeeded_logs(), key=lambda log: log.get_name())
        self.assertEqual([log.get_name() for log in logs], ['r1', 'r2'])
        self.assertIn('show version', str(logs[0]))

    def testLogToFile(self):
        # The directory is created, and each host gets its log file.
        logdir = os.path.join(self.enterContext(tempfile.TemporaryDirectory()), 'logs')

        def show_version(job, host, conn):
            conn.execute('show version')

        log_to_file(logdir)(show_version)
        self.assertEqual(os.listdir(logdir), [])
        self.runQueue(show_version, [Host('dummy://r1')])
        self.assertEqual(os.listdir(logdir), ['r1.log'])
        with open(os.path.join(logdir, 'r1.log'), encoding='utf-8') as fp:
            self.assertIn('show version', fp.read())


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(logTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
