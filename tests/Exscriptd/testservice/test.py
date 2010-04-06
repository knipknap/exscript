print "Hello Test-Service!"

def run(order, conn):
    """
    Called whenever a host that is associated with an order was contacted.
    """
    hostname = conn.get_host().get_name()
    print "Hello from test-service run()!", order.id, hostname
