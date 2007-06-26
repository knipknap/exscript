import threading
import time
from MainLoop import MainLoop

class WorkQueue:
    def __init__(self, *args, **kwargs):
        self.main_loop       = MainLoop()
        self.main_loop.debug = kwargs.get('debug', 0)
        if kwargs.has_key('max_connections'):
            self.main_loop.set_max_connections(kwargs['max_connections'])
        self.main_loop.start()

    def set_max_connections(self, max_connections):
        assert max_connections is not None
        self.main_loop.set_max_connections(max_connections)

    def enqueue(self, action):
        self.main_loop.enqueue(action)

    def start(self):
        self.main_loop.resume()

    def stop(self):
        self.main_loop.pause()

    def shutdown(self):
        self.main_loop.shutdown()
        self.main_loop.join()

    def is_paused(self):
        return self.main_loop.is_paused()

    def get_queue_length(self):
        return self.main_loop.get_queue_length()
