import os
from lxml                    import etree
from DirWatcher              import monitor
from Order                   import Order
from Exscript                import Host
from Exscript.util.decorator import bind

class INotifyDaemon(object):
    def __init__(self,
                 name,
                 directory  = None,
                 database   = None,
                 queue      = None,
                 processors = None,
                 services   = None):
        self.name       = name
        self.input_dir  = os.path.join(directory, 'in')
        self.output_dir = os.path.join(directory, 'out')
        self.db         = database
        self.processors = processors
        self.services   = services
        self.queue      = queue
        if not os.path.isdir(self.input_dir):
            os.makedirs(self.input_dir)
        if not os.path.isdir(self.output_dir):
            os.makedirs(self.output_dir)

    def _run_service(self, conn, order):
        service_name = order.get_service()
        hostname     = conn.get_host().get_name()
        print "Running service", service_name, "on", hostname
        order.set_status('in-progress')
        service = self.services[service_name]
        service.call(conn, order)

    def _save_order(self, order):
        outfile = os.path.join(self.output_dir, order.get_filename())
        order.write(outfile)

    def _on_task_done(self, order):
        print 'Order done:', order.get_id()
        order.set_status('completed')
        self._save_order(order)

    def _on_order_received(self, filename):
        if os.path.basename(filename).startswith('.'):
            return
        print 'Order received:', filename

        # Parse the order.
        try:
            order = Order.from_xml_file(filename)
        except etree.XMLSyntaxError:
            print 'Error: invalid order: ' + filename
            return
        finally:
            os.remove(filename)

        # Read the ID from the filename.
        basename = os.path.basename(filename)
        order.id = os.path.splitext(basename)[0]

        # Prepare the list of hosts from the order.
        hosts = [Host(h) for h in order.get_hosts()]
        for host in hosts:
            host.set_logname(os.path.join(order.id, host.get_logname()))

        # Enqueue it.
        task = self.queue.run(hosts, bind(self._run_service, order))
        task.signal_connect('done', self._on_task_done, order)
        order.set_status('queued')
        self._save_order(order)

    def run(self):
        #FIXME: read existing orders on startup.
        print 'Inotify daemon "' + self.name + '" running on ' + self.input_dir
        monitor(self.input_dir, self._on_order_received)
