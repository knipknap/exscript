import os
from Order import Order

class Client(object):
    def __init__(self, directory):
        self.directory = directory

    def _get_filename(self, order):
        return os.path.join(self.directory, order.id + '.xml')

    def place_order(self, order):
        if order.get_status() != 'new':
            msg = 'forbidden order status "%"' % order.get_status()
            raise ValueError(msg)
        if not order.is_valid():
            raise ValueError('incomplete or invalid order')

        order.set_status('accepted')
        filename = self._get_filename(order)
        order.write(filename)
        order.set_status('placed')

    def get_status(self, order):
        filename = self._get_filename(order)

if __name__ == '__main__':
    client = Client('/home/sab/exscriptd/in')
    order  = Order('testservice')
    client.place_order(order)
    print "Placed order", order.get_id()
