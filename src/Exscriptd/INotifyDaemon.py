import os
from lxml                    import etree
from Daemon                  import Daemon
from DirWatcher              import monitor
from Order                   import Order
from Exscript                import Host
from Exscript.util.decorator import bind

class INotifyDaemon(Daemon):
    def __init__(self,
                 name,
                 directory  = None,
                 database   = None,
                 processors = None):
        Daemon.__init__(self, name, database, processors)
        self.input_dir = os.path.join(directory, 'in')
        if not os.path.isdir(self.input_dir):
            os.makedirs(self.input_dir)

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
        self._place_order(order)

    def run(self):
        #FIXME: read existing orders on startup.
        print 'Inotify daemon "' + self.name + '" running on ' + self.input_dir
        monitor(self.input_dir, self._on_order_received)
