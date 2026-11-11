import io
import logging
import os
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stderr
from itertools import islice

from LogTest import FakeError
from util.reportTest import FakeJob

from Exscript.logger import Log, Logger, getConsoleLogger, setupLogging


def count(iterable):
    return sum(1 for _ in iterable)


def nth(iterable, n, default=None):
    "Returns the nth item or a default value"
    return next(islice(iterable, n, None), default)


class LoggerTest(unittest.TestCase):
    CORRELATE = Logger

    def setUp(self):
        self.logger = Logger()
        self.job = FakeJob('fake')

    def tearDown(self):
        # Needed to make sure that events are disconnected.
        self.logger = None

    def testConstructor(self):
        logger = Logger()

    def testGetSucceededActions(self):
        self.assertEqual(self.logger.get_succeeded_actions(), 0)

        job1 = FakeJob()
        job2 = FakeJob()
        self.assertEqual(self.logger.get_succeeded_actions(), 0)

        self.logger.add_log(id(job1), job1.name, 1)
        self.logger.add_log(id(job2), job2.name, 1)
        self.assertEqual(self.logger.get_succeeded_actions(), 0)

        self.logger.log_succeeded(id(job1))
        self.assertEqual(self.logger.get_succeeded_actions(), 1)

        try:
            raise FakeError()
        except FakeError:
            self.logger.log_aborted(id(job2), sys.exc_info())
        self.assertEqual(self.logger.get_succeeded_actions(), 1)

    def testGetAbortedActions(self):
        self.assertEqual(self.logger.get_aborted_actions(), 0)

        job = FakeJob()
        self.assertEqual(self.logger.get_aborted_actions(), 0)

        self.logger.add_log(id(job), job.name, 1)
        self.assertEqual(self.logger.get_aborted_actions(), 0)

        self.logger.log_succeeded(id(job))
        self.assertEqual(self.logger.get_aborted_actions(), 0)

        try:
            raise FakeError()
        except FakeError:
            self.logger.log_aborted(id(job), sys.exc_info())
        self.assertEqual(self.logger.get_aborted_actions(), 1)

    def testGetLogs(self):
        self.assertEqual(count(self.logger.get_logs()), 0)

        job = FakeJob()
        self.assertEqual(count(self.logger.get_logs()), 0)

        self.logger.add_log(id(job), job.name, 1)
        self.assertEqual(count(self.logger.get_logs()), 1)
        self.assertIsInstance(nth(self.logger.get_logs(), 0), Log)

        self.logger.log(id(job), 'hello world')
        self.assertEqual(count(self.logger.get_logs()), 1)

        self.logger.log_succeeded(id(job))
        self.assertEqual(count(self.logger.get_logs()), 1)

        try:
            raise FakeError()
        except FakeError:
            self.logger.log_aborted(id(job), sys.exc_info())
        self.assertEqual(count(self.logger.get_logs()), 1)

    def testGetSucceededLogs(self):
        self.assertEqual(count(self.logger.get_succeeded_logs()), 0)

        job = FakeJob()
        self.assertEqual(count(self.logger.get_succeeded_logs()), 0)

        self.logger.add_log(id(job), job.name, 1)
        self.assertEqual(count(self.logger.get_succeeded_logs()), 0)

        self.logger.log(id(job), 'hello world')
        self.assertEqual(count(self.logger.get_succeeded_logs()), 0)

        self.logger.log_succeeded(id(job))
        self.assertEqual(count(self.logger.get_aborted_logs()), 0)
        self.assertEqual(count(self.logger.get_succeeded_logs()), 1)
        self.assertIsInstance(nth(self.logger.get_succeeded_logs(), 0), Log)

    def testGetAbortedLogs(self):
        self.assertEqual(count(self.logger.get_aborted_logs()), 0)

        job = FakeJob()
        self.assertEqual(count(self.logger.get_aborted_logs()), 0)

        self.logger.add_log(id(job), job.name, 1)
        self.assertEqual(count(self.logger.get_aborted_logs()), 0)

        self.logger.log(id(job), 'hello world')
        self.assertEqual(count(self.logger.get_aborted_logs()), 0)

        try:
            raise FakeError()
        except FakeError:
            self.logger.log_aborted(id(job), sys.exc_info())
        self.assertEqual(count(self.logger.get_succeeded_logs()), 0)
        self.assertEqual(count(self.logger.get_aborted_logs()), 1)
        self.assertIsInstance(nth(self.logger.get_aborted_logs(), 0), Log)

    # The helpers return the log, so that the steps build on each other, also
    # with the checks that FileLoggerTest adds; test methods must return None.
    def _addLog(self):
        self.assertEqual(count(self.logger.get_logs()), 0)
        log = self.logger.add_log(id(self.job), self.job.name, 1)
        self.assertEqual(count(self.logger.get_logs()), 1)
        self.assertEqual(str(log), '')
        return log

    def _log(self):
        log = self._addLog()
        self.logger.log(id(self.job), 'hello world')
        self.assertEqual(str(log), 'hello world')
        return log

    def _logAborted(self):
        log = self._log()
        try:
            raise FakeError()
        except Exception:
            self.logger.log_aborted(id(self.job), sys.exc_info())
        self.assertIn('FakeError', str(log))
        return log

    def _logSucceeded(self):
        log = self._log()
        self.logger.log_succeeded(id(self.job))
        self.assertEqual(str(log), 'hello world')
        return log

    def testAddLog(self):
        self._addLog()

    def testLog(self):
        self._log()

    def testLogAborted(self):
        self._logAborted()

    def testLogSucceeded(self):
        self._logSucceeded()


class ListHandler(logging.Handler):
    """Collects the records that pass its filters."""

    def __init__(self):
        logging.Handler.__init__(self)
        self.records = []

    def emit(self, record):
        self.records.append(record)


class LoggingSetupTest(unittest.TestCase):
    """getConsoleLogger() and setupLogging(), the logging of the Python loggers."""

    def getConsoleLogger(self, name, **kwargs):
        # The handler writes to the stream that is sys.stderr when it is created.
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            logger = getConsoleLogger(name, **kwargs)
        self.addCleanup(self.resetLogger, logger)
        return logger, stderr

    def resetLogger(self, logger):
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()
        logger.setLevel(logging.NOTSET)
        logger.propagate = True

    def testGetConsoleLogger(self):
        logger, stderr = self.getConsoleLogger('LoggerTest.console', level=logging.INFO)
        self.assertIs(logger, logging.getLogger('LoggerTest.console'))
        self.assertFalse(logger.propagate)
        logger.debug('below the level of the handler')
        logger.info('connected')
        self.assertEqual(stderr.getvalue(), 'INFO: LoggerTest.console (MainThread) connected\n')

        # A logger that has a console handler is returned unchanged.
        again, _ = self.getConsoleLogger('LoggerTest.console', level=logging.DEBUG)
        self.assertIs(again, logger)
        self.assertEqual(len(logger.handlers), 1)
        logger.debug('below the level of the handler')
        self.assertEqual(stderr.getvalue(), 'INFO: LoggerTest.console (MainThread) connected\n')

    def testGetConsoleLoggerWithFileHandler(self):
        # A FileHandler is a StreamHandler, but it does not write to the console.
        tmpdir = self.enterContext(tempfile.TemporaryDirectory())
        filename = os.path.join(tmpdir, 'test.log')
        logging.getLogger('LoggerTest.file').addHandler(
            logging.FileHandler(filename, encoding='utf-8', delay=True)
        )
        logger, stderr = self.getConsoleLogger('LoggerTest.file')
        self.assertEqual(len(logger.handlers), 2)
        logger.info('connected')
        self.assertEqual(stderr.getvalue(), 'INFO: LoggerTest.file (MainThread) connected\n')
        logger.handlers[0].close()
        with open(filename, encoding='utf-8') as fp:
            self.assertEqual(fp.read(), 'connected\n')

    def testGetConsoleLoggerTimestamps(self):
        record = logging.makeLogRecord({'msg': 'hello', 'created': 0.0, 'msecs': 0.0})
        fmt = '%(asctime)s %(message)s'
        utc, _ = self.getConsoleLogger('LoggerTest.utc', fmt=fmt)
        local, _ = self.getConsoleLogger('LoggerTest.local', fmt=fmt, utc=False)
        self.assertEqual(utc.handlers[0].format(record), '1970-01-01 00:00:00,000 hello')
        expected = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(0)) + ',000 hello'
        self.assertEqual(local.handlers[0].format(record), expected)

    def setupLogging(self, **kwargs):
        # Calls setupLogging() with loggers that are not registered in the
        # logging module, so that the test changes no global logger.
        loggers = {}

        def init(name):
            logger = logging.Logger(name)
            logger.addHandler(ListHandler())
            loggers[name] = logger
            return logger

        setupLogging(init=init, **kwargs)
        return loggers

    def passes(self, logger, name):
        # Whether the handler of the logger passes a record of the logger with the given name.
        handler = logger.handlers[0]
        handler.records.clear()
        logger.handle(logging.LogRecord(name, logging.INFO, __file__, 1, 'message', None, None))
        return len(handler.records) == 1

    def testSetupLogging(self):
        loggers = self.setupLogging()
        names = {
            'Exscript',
            'Exscript.interpreter.parser',
            'Exscript.parselib.lexer',
            'Exscript.protocols',
            'Exscript.servers',
            'ncclient.capabilities',
            'ncclient.devices',
            'ncclient.manager',
            'ncclient.operations',
            'ncclient.transport.session',
            'ncclient.transport.ssh',
            'paramiko.transport',
        }
        self.assertEqual(set(loggers), names)
        for name, logger in loggers.items():
            self.assertFalse(self.passes(logger, name), name)

    def testSetupLoggingPackage(self):
        loggers = self.setupLogging(package=True)
        self.assertTrue(self.passes(loggers['Exscript'], 'Exscript'))
        self.assertTrue(self.passes(loggers['Exscript'], 'Exscript.queue'))
        self.assertFalse(self.passes(loggers['Exscript'], 'ExscriptX'))
        self.assertFalse(self.passes(loggers['Exscript.protocols'], 'Exscript.protocols.ssh2'))
        self.assertFalse(self.passes(loggers['paramiko.transport'], 'paramiko.transport'))

    def testSetupLoggingParser(self):
        loggers = self.setupLogging(parser=True)
        self.assertTrue(self.passes(loggers['Exscript.parselib.lexer'], 'Exscript.parselib.lexer'))
        logger = loggers['Exscript.interpreter.parser']
        self.assertTrue(self.passes(logger, 'Exscript.interpreter.parser'))
        self.assertFalse(self.passes(loggers['Exscript'], 'Exscript.queue'))

    def testSetupLoggingProtocol(self):
        loggers = self.setupLogging(protocol=True)
        logger = loggers['Exscript.protocols']
        self.assertTrue(self.passes(logger, 'Exscript.protocols'))
        self.assertTrue(self.passes(logger, 'Exscript.protocols.ssh2'))
        self.assertFalse(self.passes(logger, 'Exscript.protocolsX'))
        self.assertTrue(self.passes(loggers['Exscript.servers'], 'Exscript.servers.sshd'))
        self.assertTrue(self.passes(loggers['paramiko.transport'], 'paramiko.transport'))
        logger = loggers['ncclient.transport.ssh']
        self.assertTrue(self.passes(logger, 'ncclient.transport.ssh'))
        self.assertFalse(self.passes(loggers['Exscript'], 'Exscript.queue'))


def suite():
    loader = unittest.TestLoader()
    return unittest.TestSuite(
        [
            loader.loadTestsFromTestCase(LoggerTest),
            loader.loadTestsFromTestCase(LoggingSetupTest),
        ]
    )


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
