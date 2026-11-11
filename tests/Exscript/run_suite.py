#!/usr/bin/env python3
import fnmatch
import functools
import glob
import logging
import os
import re
import sys
import time
import unittest
from inspect import isclass, isfunction, ismodule

logger = logging.getLogger('TestSuite')
logger.addHandler(logging.NullHandler())


def uppercase(match):
    return match.group(1).upper()


correlated = dict()


def setup_logging(filename=None):
    logformat = "%(levelname)s: %(name)s (%(threadName)s) %(message)s"
    loglevel = logging.DEBUG
    logger_names = [
        "Exscript",
        "Exscript.interpreter.parser",
        "Exscript.parselib.lexer",
        "Exscript.protocols",
        "Exscript.servers",
        # Netconf Client
        "ncclient.capabilities",
        "ncclient.devices",
        "ncclient.manager",
        "ncclient.operations",
        "ncclient.transport.session",
        "ncclient.transport.ssh",
        # Paramiko
        "paramiko.transport",
        # Tests may also log.
        "TestSuite",
    ]
    formatter = logging.Formatter(logformat)
    formatter.converter = time.gmtime
    if filename is None:
        handler = logging.StreamHandler(sys.stderr)
    else:
        handler = logging.FileHandler(filename, mode="w", encoding="utf8")
    handler.setFormatter(formatter)
    handler.setLevel(loglevel)
    for name in logger_names:
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        logger.propagate = False


def log_suites(suites):
    for item in suites:
        if isinstance(item, unittest.TestSuite):
            log_suites(item)  # suites are iterable
        elif isinstance(item, unittest.TestCase):
            testname = item.id()
            method_names = (
                'setUpClass',
                'setUp',
                testname.split('.')[-1],
                'tearDown',
                'tearDownClass',
            )
            for name in method_names:
                method = getattr(item, name, None)
                if not method:
                    continue
                msg = 'Running %s (%s)' % (name, testname)
                setattr(item, name, log_call(msg)(method))
        else:
            raise TypeError("Unexpected type: %s" % type(item))


def log_call(msg):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger.debug(msg)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def correlate_class(theclass):
    """
    Checks the given testcase for missing test methods.
    """
    if not hasattr(theclass, 'CORRELATE'):
        return

    # Collect all functions in the class or module.
    for name, value in list(theclass.CORRELATE.__dict__.items()):
        if not isfunction(value):
            continue
        elif name == '__init__':
            name = 'Constructor'
        elif name.startswith('_'):
            continue

        # Format the function names.
        testname = re.sub(r'_(\w)', uppercase, name)
        testname = re.sub(r'(\d\w)', uppercase, testname)
        testname = 'test' + re.sub(r'^(\w)', uppercase, testname)
        testmethod = theclass.__name__ + '.' + testname
        method = theclass.CORRELATE.__name__ + '.' + name
        both = testmethod + ' (' + method + ')'

        # Throw an error if the function does not have a test.
        if testname in dir(theclass):
            continue
        if ismodule(theclass.CORRELATE) and value.__module__ != theclass.CORRELATE.__name__:
            continue  # function was imported.
        if both in correlated:
            continue
        correlated[both] = True
        if ismodule(theclass.CORRELATE):
            sys.stderr.write('!!!! WARNING: Untested function: ' + both + '\n')
        elif isclass(theclass.CORRELATE):
            sys.stderr.write('!!!! WARNING: Untested method: ' + both + '\n')


def correlate_module(module):
    """
    Checks all testcases in the module for missing test methods.
    """
    for name, item in list(module.__dict__.items()):
        if isclass(item):
            correlate_class(item)


def find(dirname, pattern):
    output = []
    for root, dirs, files in os.walk(dirname):
        for file in files:
            if fnmatch.fnmatchcase(file, pattern):
                output.append(os.path.join(root, file))
    return output


def load_suite(files):
    modules = [os.path.splitext(f)[0] for f in files]
    modules.sort()
    all_suites = []
    for name in modules:
        name = name.lstrip('.').lstrip('/').replace('/', '.')
        module = __import__(name, globals(), locals(), [''])
        all_suites.append(module.suite())
        correlate_module(module)
    if correlated:
        sys.stderr.write('Error: Untested methods found.\n')
        sys.exit(1)
    log_suites(all_suites)
    return unittest.TestSuite(all_suites)


def suite():
    pattern = os.path.join(os.path.dirname(__file__), '*Test.py')
    files = glob.glob(pattern)
    return load_suite([os.path.basename(f) for f in files])


def recursive_suite():
    return load_suite(find('.', '*Test.py'))


if __name__ == '__main__':
    # Parse CLI options.
    if len(sys.argv) == 1:
        verbosity = 2
    elif len(sys.argv) == 2:
        verbosity = int(sys.argv[1])
    else:
        print('Syntax:', sys.argv[0], '[verbosity]')
        print('Default verbosity is 2')
        sys.exit(1)

    # Run.
    logfile = os.path.splitext(__file__)[0] + '.log'
    setup_logging(logfile)
    unittest.TextTestRunner(verbosity=verbosity).run(recursive_suite())
    print('Logfile with Exscript and TestSuite activity: %s' % logfile)
