print "Hello Python-Service!"

def run(service, order, conn):
    """
    Called whenever a host that is associated with an order was contacted.
    """
    hostname = conn.get_host().get_name()
    print "Hello from python-service run()!", service.name, order.id, hostname

def enter(service, order):
    """
    Called whenever a new order was received.
    If this funtion returns True the order is accepted. Otherwise,
    the order is rejected.
    """
    print "Hello from python-service enter()!", service.name, order.id
    return True
