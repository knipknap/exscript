from lxml import etree

class Order(object):
    def __init__(self, service_name, hosts):
        self.service_name = service_name
        self.hosts        = hosts

    @staticmethod
    def from_xml_file(filename):
        cfgtree = etree.parse(filename)
        order   = cfgtree.find('order')
        service = order.get('service').strip()
        hosts   = [h.get('address').strip() for h in order.iterfind('host')]
        return Order(service, hosts)
