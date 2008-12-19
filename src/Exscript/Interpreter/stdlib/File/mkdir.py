import os

def execute(scope, dirnames, mode = None):
    for dirname in dirnames:
        if mode is None:
            os.makedirs(dirname)
        else:
            os.makedirs(dirname, mode[0])
    return 1
