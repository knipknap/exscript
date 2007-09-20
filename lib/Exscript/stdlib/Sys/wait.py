import time

signature = [('self', 'integer')]

def execute(scope, seconds):
    time.sleep(int(seconds[0]))
    return 1
