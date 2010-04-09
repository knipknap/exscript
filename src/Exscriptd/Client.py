import os
from Order                 import Order
from sqlalchemy.exceptions import InvalidRequestError
from Config                import Config

class Client(object):
    def __init__(self, config_file, server_name):
        config          = Config(config_file)
        directory       = config.get_inotify_daemon_dir(server_name)
        database_name   = config.get_inotify_daemon_db_name(server_name)
        self.db         = config.init_database_from_name(database_name)
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
    if len(sys.argv) == 4:
        config      = sys.argv[1]
        daemon_name = sys.argv[2]
        order       = Order.from_xml_file(sys.argv[3])
    else:
        sys.stderr.write('Syntax: config daemon-name order\n')
        sys.exit(1)

    client = Client(config, daemon_name)
    print "Status:", client.get_order_status_from_id(order.id)
    client.place_order(order)
    print "Placed order", order.id
    status = client.get_order_status_from_id(order.id)

    while status != 'completed':
        print "Status:", status
        time.sleep(.1)
        status = client.get_order_status_from_id(order.id)

    print "Status:", status
