import os
from Order import Order

class Client(object):
    def __init__(self, directory):
        self.input_dir  = os.path.join(directory, 'in')
        self.output_dir = os.path.join(directory, 'out')

    def place_order(self, order):
        if order.get_status() != 'new':
            msg = 'order status is "%s", should be "new"' % order.get_status()
            raise ValueError(msg)
        if not order.is_valid():
            raise ValueError('incomplete or invalid order')

        order.set_status('accepted')
        filename = os.path.join(self.input_dir, order.get_filename())
        order.write(filename)
        order.set_status('placed')

    def get_order_status(self, order_id):
        order        = Order('')
        order.id     = order_id
        in_filename  = os.path.join(self.input_dir,  order.get_filename())
        out_filename = os.path.join(self.output_dir, order.get_filename())
        if os.path.exists(in_filename):
            return 'new'
        if not os.path.exists(out_filename):
            return 'none'
        order = Order.from_xml_file(out_filename)
        return order.get_status()

if __name__ == '__main__':
    import sys, time
    if len(sys.argv) == 2:
        order = Order.from_xml_file(sys.argv[1])
    else:
        order = Order('testservice')

    client = Client('/home/sab/exscriptd')
    print "Status:", client.get_order_status(order.get_id())
    client.place_order(order)
    print "Placed order", order.get_id()
    status = client.get_order_status(order.get_id())

    while status != 'completed':
        print "Status:", status
        time.sleep(.1)
        status = client.get_order_status(order.get_id())

    print "Status:", status
