import os

def execute(scope, filenames):
    for filename in filenames:
        os.remove(filename)
    return 1
