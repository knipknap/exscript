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
        self.db_cls     = database
        self.processors = processors
        self.services   = services
        self.queue      = queue
        if not os.path.isdir(self.input_dir):
            os.makedirs(self.input_dir)
        if not os.path.isdir(self.output_dir):
            os.makedirs(self.output_dir)

    def _set_order_status(self, db, order, status):
        order.status = status
        db.save_or_update(order)
        db.commit()

    def _get_order_from_id(self, db, order_id):
        return db.query(Order).filter(Order.id == order_id).one()

    def _run_service(self, conn, order_id):
        db           = self.db_cls()
        order        = self._get_order_from_id(db, order_id)
        service_name = order.service
        hostname     = conn.get_host().get_name()
        service      = self.services[service_name]
        print "Running service", service_name, "on", hostname
        self._set_order_status(db, order, 'in-progress')
        service.call(conn, order)
        self._set_order_status(db, order, 'service-done')

    def _on_task_done(self, order_id):
        print 'Order done:', order_id
        db    = self.db_cls()
        order = self._get_order_from_id(db, order_id)
        self._set_order_status(db, order, 'completed')
        outfile = os.path.join(self.output_dir, order.get_filename())
        order.write(outfile)

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
        hosts = [Host(h.address) for h in order.hosts]
        for host in hosts:
            host.set_logname(os.path.join(order.id, host.get_logname()))

        # Store it in the database.
        db = self.db_cls()
        self._set_order_status(db, order, 'accepted')

        # Enqueue it.
        task = self.queue.run(hosts, bind(self._run_service, order.id))
        task.signal_connect('done', self._on_task_done, order.id)
        self._set_order_status(db, order, 'queued')

    def run(self):
        #FIXME: read existing orders on startup.
        print 'Inotify daemon "' + self.name + '" running on ' + self.input_dir
        monitor(self.input_dir, self._on_order_received)
