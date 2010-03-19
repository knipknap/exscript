from lxml import etree
from util import mkorderid

class Order(object):
    def __init__(self, service_name):
        self.id    = mkorderid(service_name)
        self.xml   = etree.Element('xml')
        self.order = etree.SubElement(self.xml,
                                      'order',
                                      service = service_name)
        self.set_status('new')

    @staticmethod
    def from_xml_file(filename):
        order     = Order('')
        order.xml = etree.parse(filename)
        return order

    def toxml(self):
        return etree.tostring(self.xml)

    def write(self, filename):
        file = open(filename, 'w')
        file.write(self.toxml())
        file.close()

    def is_valid(self):
        return True #FIXME

    def get_id(self):
        return self.id

    def set_status(self, status):
        assert status in ('new',
                          'accepted',
                          'placed',
                          'queued',
                          'in-progress',
                          'completed',
                          'error')
        return self.order.set('status', status)

    def get_status(self):
        return self.order.get('status')

    def get_service(self):
        return self.order.get('service').strip()

    def add_host(self, host):
        etree.SubElement(self.order, 'host', address = host)

    def get_hosts(self):
        return [h.get('address').strip() for h in self.order.iterfind('host')]
