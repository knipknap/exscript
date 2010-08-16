import os
from threading               import Lock
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
        self.task_lock = Lock()
        self.tasks     = {}   # Maps order ids to lists of tasks.

    def get_logname(self, order, name = ''):
        return os.path.join(self.daemon.get_logdir(),
                            self.name,
                            str(order.get_id()),
                            name)

    def _update_host_logname(self, order, host):
        host.set_logname(self.get_logname(order, host.get_logname()))

    def config_file(self, name):
        return os.path.join(self.cfg_dir, name)

    def _track_task(self, order, task):
        with self.task_lock:
            task.signal_connect('done', self._task_done, order, task)
            if self.tasks.has_key(order.id):
                self.tasks[order.id].append(task)
            else:
                self.tasks[order.id] = [task]

    def _task_done(self, order, task):
        with self.task_lock:
            self.tasks[order.id].remove(task)
            if not self.tasks[order.id]:
                del self.tasks[order.id]
                self.done(order)

    def enqueue_hosts(self, order, hosts, callback):
        hosts = order.get_hosts()
        for host in hosts:
            self._update_host_logname(order, host)

        # For performance reasons, we defer the starting of further
        # threads by pausing the queue.
        # We also need to pause to avoid getting a 'done' signal before
        # the signal is connected.
        self.queue.workqueue.pause()
        task = self.queue.run(hosts, callback)
        self._track_task(order, task)
        self.queue.workqueue.unpause()
        return task

    def enqueue(self, order, function, name):
        name = self.get_logname(order, name)
        self.queue.workqueue.pause()
        task = self.queue.enqueue(function, name)
        self._track_task(order, task)
        self.queue.workqueue.unpause()
        return task

    def enter(self, order):
        return True

    def done(self, order):
        self.daemon.set_order_status_done(order)

    def set_order_status(self, order, status):
        self.daemon.set_order_status(order, status)

    def save_order(self, order):
        self.daemon.save_order(order)
