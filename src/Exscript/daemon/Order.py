import os, shutil
from sqlalchemy     import *
from sqlalchemy.orm import relation, synonym
from Database       import Base
from tempfile       import NamedTemporaryFile
from lxml           import etree
from util           import mkorderid

class Order(Base):
    __tablename__ = 'order'
    id            = Column(String(50), primary_key = True)
    service       = Column(String(50), index = True)
    status        = Column(String(20), index = True)

    def __init__(self, service_name):
        Base.__init__(self,
                      id      = mkorderid(service_name),
                      status  = 'new',
                      service = service_name)

    def __repr__(self):
        return "<Order('%s','%s','%s')>" % (self.id, self.service, self.status)

    @staticmethod
    def from_xml_file(filename):
        # Parse required attributes.
        xml     = etree.parse(filename)
        element = xml.find('order')
        order   = Order(element.get('service'))
        order._read_hosts_from_xml(element)
        return order

    def _read_hosts_from_xml(self, element):
        for host in element.iterfind('host'):
            address = host.get('address').strip()
            self.hosts.append(Host(address))

    def fromxml(self, xml):
        xml = etree.fromstring(xml)
        self._read_hosts_from_xml(xml.find('order'))

    def toxml(self):
        xml   = etree.Element('xml')
        order = etree.SubElement(xml, 'order', service = self.service)
        for host in self.hosts:
            etree.SubElement(order, 'host', address = host.address)
        return etree.tostring(xml)

    def write(self, filename):
        dirname  = os.path.dirname(filename)
        file     = NamedTemporaryFile(dir = dirname, prefix = '.') #delete = False)
        file.write(self.toxml())
        file.flush()
        os.rename(file.name, filename)
        try:
            file.close()
        except:
            pass

    def is_valid(self):
        return True #FIXME

    def get_filename(self):
        return self.id + '.xml'

class Host(Base):
    __tablename__ = 'host'

    order_id = Column(String(50),  ForeignKey('order.id'), primary_key = True)
    address  = Column(String(150), primary_key = True)
    name     = Column(String(50),  primary_key = True)
    hosts    = relation(Order,
                        backref  = 'hosts',
                        order_by = Order.id)

    def __init__(self, address):
        Base.__init__(self, address = address, name = address)
