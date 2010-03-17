from lxml import etree

class Order(object):
    def __init__(self, service_name, hosts):
        self.service_name = service_name
        self.hosts        = hosts
        self.filename     = None

    @staticmethod
    def from_xml_file(filename):
        cfgtree        = etree.parse(filename)
        element        = cfgtree.find('order')
        service        = element.get('service').strip()
        hosts          = element.iterfind('host')
        addresses      = [h.get('address').strip() for h in hosts]
        order          = Order(service, addresses)
        order.filename = filename
        return order
