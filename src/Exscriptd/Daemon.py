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
        self.db_cls     = database
        self.processors = processors
        self.services   = {}

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
