from Exscript.util.decorator import bind
from Task                    import Task

class Service(Task):
    def __init__(self,
                 daemon,
                 name,
                 actions,
                 queue     = None,
                 autoqueue = False):
        Task.__init__(self, name, actions)
        self.daemon    = daemon
        self.queue     = queue
        self.autoqueue = autoqueue

        if self.autoqueue and not self.queue:
            raise Exception('error: autoqueue requires a queue')

    def enter(self, order):
        if not self.autoqueue:
            return True
        task = self.queue.run(order.get_hosts(), bind(self.run, order.id))
        task.signal_connect('done', self.daemon.order_done, order.id)
        self.daemon.set_order_status(order, 'queued')
        return True
