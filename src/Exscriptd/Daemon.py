import os
from lxml                    import etree
from Order                   import Order
from Exscript                import Host
from Exscript.util.decorator import bind

class Daemon(object):
    def __init__(self,
                 name,
                 database   = None,
                 processors = None):
        self.name       = name
        self.db         = database
        self.processors = processors
        self.services   = {}

    def add_service(self, name, service):
        self.services[name] = service

    def set_order_status(self, order, status):
        order.status = status
        self.db.save_order(order)

    def get_order_from_id(self, order_id):
        return self.db.get_order(id = order_id)

    def order_done(self, order_id):
        print 'Order done:', order_id
        order = self.db.get_order(id = order_id)
        self.set_order_status(order, 'completed')

    def _place_order(self, order):
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

        self.set_order_status(order, 'accepted')
