import os
from Exscript.util.decorator import bind

class Service(object):
    def __init__(self,
                 daemon,
                 name,
                 cfg_dir,
                 queue = None):
        self.cfg_dir   = cfg_dir
        self.daemon    = daemon
        self.name      = name
        self.queue     = queue

    def config_file(self, name):
        return os.path.join(self.cfg_dir, name)

    def enqueue_hosts(self, order, hosts, callback):
        # For performance reasons, we defer the starting of further
        # threads by pausing the queue.
        self.queue.workqueue.pause()
        task = self.queue.run(order.get_hosts(), callback)
        task.signal_connect('done', self.daemon.order_done, order.id)
        self.daemon.set_order_status(order, 'queued')
        self.queue.workqueue.unpause()

    def enqueue(self, function, name):
        task = self.queue.enqueue(function, name)
        self.queue.workqueue.unpause()
        return task

    def enter(self, order):
        return True
