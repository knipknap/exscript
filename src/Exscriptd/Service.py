from Exscript.util.decorator import bind

class Service(object):
    def __init__(self,
                 daemon,
                 name,
                 queue     = None,
                 autoqueue = False):
        self.daemon      = daemon
        self.name        = name
        self.queue       = queue
        self.autoqueue   = autoqueue

        if self.autoqueue and not self.queue:
            raise Exception('error: autoqueue requires a queue')

    def _autoqueue(self, order):
        if not self.autoqueue:
            return
        # For performance reasons, we defer the starting of further
        # threads by pausing the queue.
        self.queue.workqueue.pause()
        task = self.queue.run(order.get_hosts(), bind(self.run, order.id))
        task.signal_connect('done', self.daemon.order_done, order.id)
        self.daemon.set_order_status(order, 'queued')
        self.queue.workqueue.unpause()

    def enter(self, order):
        self._autoqueue(order)
        return True

    def run(self, conn, order_id):
        hostname = conn.get_host().get_name()
        print "Running service", self.name, "on", hostname
        order = self.daemon.get_order_from_id(order_id)
        self.daemon.set_order_status(order, 'in-progress')
        self.run_func(self, order, conn)
        self.daemon.set_order_status(order, 'serviced')
