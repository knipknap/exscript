import sys

signature = [('self', 'string')]

def execute(scope, string):
    sys.stdout.write(string[0] + '\n')
    sys.stdout.flush()
    return 1
