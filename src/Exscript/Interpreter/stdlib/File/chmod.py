import os

def execute(scope, filenames, mode):
    for filename in filenames:
        os.chmod(filename, mode[0])
    return 1
