#!/usr/bin/python
import os, sys, unittest, glob, fnmatch

def find(dirname, pattern):
    output = []
    for root, dirs, files in os.walk(dirname):
        for file in files:
            if fnmatch.fnmatchcase(file, pattern):
                output.append(os.path.join(root, file))
    return output

def load_suite(files):
    modules    = [os.path.splitext(f)[0] for f in files]
    all_suites = []
    for name in modules:
        name   = name.lstrip('.').lstrip('/').replace('/', '.')
        module = __import__(name, globals(), locals(), [''])
        all_suites.append(module.suite())
    return unittest.TestSuite(all_suites)

def suite():
    pattern = os.path.join(os.path.dirname(__file__), '*Test.py')
    files   = glob.glob(pattern)
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
        print 'Syntax:', sys.argv[0], '[verbosity]'
        print 'Default verbosity is 2'
        sys.exit(1)

    # Run.
    unittest.TextTestRunner(verbosity = verbosity).run(recursive_suite())
