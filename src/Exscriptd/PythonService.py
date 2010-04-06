from Exscript.util.decorator import bind

class PythonService(object):
    def __init__(self,
                 daemon,
                 name,
                 filename,
                 queue     = None,
                 autoqueue = False):
        self.daemon      = daemon
        self.name        = name
        self.queue       = queue
        self.autoqueue   = autoqueue
        content          = open(filename).read()
        code             = compile(content, filename, 'exec')
        vars             = globals().copy()
        vars['__file__'] = filename
        result           = eval(code, vars)
        self.enter_func  = vars.get('enter')
        self.run_func    = vars.get('run')

        if self.autoqueue and not self.queue:
            raise Exception('error: autoqueue requires a queue')

    def enter(self, order):
        if self.enter_func and not self.enter_func(self, order):
            return False
        if not self.autoqueue:
            return True
        task = self.queue.run(order.get_hosts(), bind(self.run, order.id))
        task.signal_connect('done', self.daemon.order_done, order.id)
        self.daemon.set_order_status(order, 'queued')
        return True

    def run(self, conn, order_id):
        hostname = conn.get_host().get_name()
        print "Running service", self.name, "on", hostname
        order = self.daemon.get_order_from_id(order_id)
        self.daemon.set_order_status(order, 'in-progress')
        self.run_func(self, order, conn)
        self.daemon.set_order_status(order, 'serviced')
