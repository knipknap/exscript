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
                 processors = None):
        self.name       = name
        self.input_dir  = os.path.join(directory, 'in')
        self.output_dir = os.path.join(directory, 'out')
        self.db_cls     = database
        self.processors = processors
        self.services   = {}
        if not os.path.isdir(self.input_dir):
            os.makedirs(self.input_dir)
        if not os.path.isdir(self.output_dir):
            os.makedirs(self.output_dir)

    def add_service(self, name, service):
        self.services[name] = service

    def get_order_from_id(self, order_id):
        db = self.db_cls()
        return db.query(Order).filter(Order.id == order_id).one()

    def set_order_status(self, order, status):
        db = self.db_cls()
        order.status = status
        db.save_or_update(order)
        db.commit()

    def order_done(self, order_id):
        print 'Order done:', order_id
        order = self.get_order_from_id(order_id)
        self.set_order_status(order, 'completed')
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

        # Store it in the database.
        self.set_order_status(order, 'incoming')

        # Loop the requested service up.
        service = self.services.get(order.service)
        if not service:
            args = order.id, order.service
            print 'Order %s: Unknown service "%s" requested' % args
            self.set_order_status(order, 'service-not-found')
            return

        # Notify the service of the new order.
        if not service.enter(order):
            args = order.id, order.service
            print 'Order %s: Rejected by service "%s"' % args
            self.set_order_status(order, 'rejected')
            return

    def run(self):
        #FIXME: read existing orders on startup.
        print 'Inotify daemon "' + self.name + '" running on ' + self.input_dir
        monitor(self.input_dir, self._on_order_received)
