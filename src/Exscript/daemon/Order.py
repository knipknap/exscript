import os, shutil
from tempfile import NamedTemporaryFile
from lxml     import etree
from util     import mkorderid

class Order(object):
    def __init__(self, service_name):
        self.id    = mkorderid(service_name)
        self.xml   = etree.Element('xml')
        self.order = etree.SubElement(self.xml,
                                      'order',
                                      service = service_name)
        self.order.set('status', 'new')

    def __repr__(self):
        return "<Order('%s','%s','%s')>" % (self.get_id(),
                                            self.get_service(),
                                            self.get_status())

    @staticmethod
    def from_xml_file(filename):
        # Parse required attributes.
        xml     = etree.parse(filename)
        element = xml.find('order')
        service = element.get('service')
        if not element.get('status'):
            element.set('status', 'new')

        # Create an order.
        order       = Order(element.get('service'))
        order.xml   = xml
        order.order = element
        return order

    def toxml(self):
        return etree.tostring(self.xml)

    def write(self, filename):
        dirname  = os.path.dirname(filename)
        file     = NamedTemporaryFile(dir = dirname, prefix = '.') #delete = False)
        file.write(self.toxml())
        file.flush()
        #if os.path.exists(filename):
        #    os.remove(filename)
        os.rename(file.name, filename)
        try:
            file.close()
        except:
            pass
        # Touch the file to trigger inotify.
        #open(filename, 'a').close()

    def is_valid(self):
        return True #FIXME

    def get_id(self):
        return self.id

    def get_filename(self):
        return self.id + '.xml'

    def set_status(self, status):
        assert status in ('accepted',
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
