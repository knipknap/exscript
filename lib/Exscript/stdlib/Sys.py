import sys, time

def wait(scope, seconds):
    time.sleep(int(seconds[0]))
    return 1

def message(scope, string):
    sys.stdout.write(string[0])
    sys.stdout.flush()
    return 1
