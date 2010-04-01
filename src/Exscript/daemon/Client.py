import os
from Order                 import Order
from sqlalchemy.exceptions import InvalidRequestError
from init                  import get_inotify_daemon_dir,       \
                                  get_inotify_daemon_db_name,   \
                                  init_database

class Client(object):
    def __init__(self, config_file, server_name):
        directory       = get_inotify_daemon_dir(config_file, server_name)
        database_name   = get_inotify_daemon_db_name(config_file, server_name)
        self.db         = init_database(config_file, database_name)
        self.input_dir  = os.path.join(directory, 'in')
        self.output_dir = os.path.join(directory, 'out')

    def place_order(self, order):
        if order.status != 'new':
            msg = 'order status is "%s", should be "new"' % order.status
            raise ValueError(msg)
        if not order.is_valid():
            raise ValueError('incomplete or invalid order')

        order.status = 'accepted'
        filename     = os.path.join(self.input_dir, order.get_filename())
        order.write(filename)
        order.status = 'placed'

    def get_order_from_id(self, order_id):
        return self.db.query(Order).filter(Order.id == order_id).one()

    def get_order_status_from_id(self, order_id):
        try:
            order = self.get_order_from_id(order_id)
        except InvalidRequestError:
            return 'not-found'
        return order.status

if __name__ == '__main__':
    import sys, time
    if len(sys.argv) == 2:
        order = Order.from_xml_file(sys.argv[1])
    else:
        order = Order('testservice')

    client = Client('/home/sab/sandbox/exscript/config.xml', 'exscript-daemon')
    print "Status:", client.get_order_status_from_id(order.id)
    client.place_order(order)
    print "Placed order", order.id
    status = client.get_order_status_from_id(order.id)

    while status != 'completed':
        print "Status:", status
        time.sleep(.1)
        status = client.get_order_status_from_id(order.id)

    print "Status:", status
