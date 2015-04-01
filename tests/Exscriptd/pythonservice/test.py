print("Hello Python-Service!")

def run(conn, order):
    """
    Called whenever a host that is associated with an order was contacted.
    """
    hostname = conn.get_host().get_name()
    print("Hello from python-service run()!", __service__.name, order.id, hostname)

def enter(order):
    """
    Called whenever a new order was received.
    If this funtion returns True the order is accepted. Otherwise,
    the order is rejected.
    """
    print("Hello from python-service enter()!", __service__.name, order.id)
    callback = bind(run, order)
    __service__.enqueue_hosts(order, order.get_hosts(), callback)
    __service__.set_order_status(order, 'queued')
    return True
