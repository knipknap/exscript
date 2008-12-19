import os.path

def execute(scope, filename):
    return [os.path.exists(filename[0])]
