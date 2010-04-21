"""
Represents a call to a service.
"""
import os, shutil
import Exscript
from sqlalchemy     import *
from sqlalchemy.orm import relation, synonym
from Database       import Base
from tempfile       import NamedTemporaryFile
from lxml           import etree
from util           import mkorderid

class Order(Base):
    """
    An order includes all information that is required to make a
    service call.
    """
    __tablename__ = 'order'
    id            = Column(String(50), primary_key = True)
    service       = Column(String(50), index = True)
    status        = Column(String(20), index = True)

    def __init__(self, service_name):
        """
        Constructor. The service_name defines the service to whom
        the order is delivered. In other words, this is the
        service name is assigned in the config file of the server.

        @type  service_name: str
        @param service_name: The service that handles the order.
        """
        Base.__init__(self,
                      id      = mkorderid(service_name),
                      status  = 'new',
                      service = service_name)

    def __repr__(self):
        return "<Order('%s','%s','%s')>" % (self.id, self.service, self.status)

    @staticmethod
    def from_xml_file(filename):
        """
        Creates a new instance by reading the given XML file.

        @type  filename: str
        @param filename: A file containing an XML formatted order.
        @rtype:  Order
        @return: A new instance of an order.
        """
        # Parse required attributes.
        xml     = etree.parse(filename)
        element = xml.find('order')
        order   = Order(element.get('service'))
        order._read_hosts_from_xml(element)
        return order

    def _read_hosts_from_xml(self, element):
        for host in element.iterfind('host'):
            address = host.get('address').strip()
            self.hosts.append(_Host(address))

    def fromxml(self, xml):
        """
        Updates the order using the values that are defined in the
        given XML string.

        @type  xml: str
        @param xml: XML
        """
        xml = etree.fromstring(xml)
        self._read_hosts_from_xml(xml.find('order'))

    def toxml(self):
        """
        Returns the order as an XML formatted string.

        @rtype:  str
        @return: The XML representing the order.
        """
        xml   = etree.Element('xml')
        order = etree.SubElement(xml, 'order', service = self.service)
        for host in self.hosts:
            etree.SubElement(order, 'host', address = host.address)
        return etree.tostring(xml)

    def write(self, filename):
        """
        Export the order as an XML file.

        @type  filename: str
        @param filename: XML
        """
        dirname  = os.path.dirname(filename)
        file     = NamedTemporaryFile(dir = dirname, prefix = '.') #delete = False)
        file.write(self.toxml())
        file.flush()
        os.chmod(file.name, 0644)
        os.rename(file.name, filename)
        try:
            file.close()
        except:
            pass

    def is_valid(self):
        """
        Returns True if the order validates, False otherwise.

        @rtype:  bool
        @return: True if the order is valid, False otherwise.
        """
        return True #FIXME

    def get_filename(self):
        """
        Creates a filename from the id.

        @rtype:  str
        @return: A filename for the order.
        """
        return self.id + '.xml'

    def get_hosts(self):
        """
        Returns Exscript.Host objects for all hosts that are
        included in the order.

        @rtype:  [Exscript.Host]
        @return: A list of hosts.
        """
        # Prepare the list of hosts from the order.
        hosts = [Exscript.Host(h.address) for h in self.hosts]
        for host in hosts:
            host.set_logname(os.path.join(self.id, host.get_logname()))
        return hosts

class _Host(Base):
    __tablename__ = 'host'

    order_id = Column(String(50),  ForeignKey('order.id'), primary_key = True)
    address  = Column(String(150), primary_key = True)
    name     = Column(String(50),  primary_key = True)
    hosts    = relation(Order,
                        backref  = 'hosts',
                        order_by = Order.id)

    def __init__(self, address):
        Base.__init__(self, address = address, name = address)
