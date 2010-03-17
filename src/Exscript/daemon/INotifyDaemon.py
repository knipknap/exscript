import os, shutil
from DirWatcher              import monitor
from Order                   import Order
from Exscript.util.decorator import bind

class INotifyDaemon(object):
    def __init__(self,
                 name,
                 input_dir  = None,
                 output_dir = None,
                 queue      = None,
                 processors = None,
                 services   = None):
        self.name       = name
        self.input_dir  = input_dir
        self.output_dir = output_dir
        self.processors = processors
        self.services   = services
        self.queue      = queue
        if not os.path.isdir(self.input_dir):
            os.makedirs(self.input_dir)
        if not os.path.isdir(self.output_dir):
            os.makedirs(self.output_dir)

    def _run_service(self, conn, service):
        print "CONN", conn.get_host().get_name(), service
        service.call(conn)
        #FIXME

    def _on_task_done(self, order):
        print "Order done:", order.filename
        basename = os.path.basename(order.filename)
        shutil.move(order.filename, self.output_dir)

    def _on_order_received(self, filename):
        print 'Order received:', filename
        order   = Order.from_xml_file(filename)
        service = self.services[order.service_name]
        task    = self.queue.run(order.hosts, bind(self._run_service, service))
        task.signal_connect('done', self._on_task_done, order)

    def run(self):
        #FIXME: read existing orders on startup.
        print 'Inotify daemon "' + self.name + '" running on ' + self.input_dir
        monitor(self.input_dir, self._on_order_received)
