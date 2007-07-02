import sys

def message(scope, string):
    sys.stdout.write(string[0])
    sys.stdout.flush()
    return 1
