# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
Represents a call to a service.
"""
import os
from getpass            import getuser
from datetime           import datetime
from tempfile           import NamedTemporaryFile
from lxml               import etree
from Exscript.util.file import get_hosts_from_csv
from Exscriptd.DBObject import DBObject
from Exscriptd.xml      import add_hosts_to_etree

class Order(DBObject):
    """
    An order includes all information that is required to make a
    service call.
    """

    def __init__(self, service_name):
        """
        Constructor. The service_name defines the service to whom
        the order is delivered. In other words, this is the
        service name is assigned in the config file of the server.

        @type  service_name: str
        @param service_name: The service that handles the order.
        """
        DBObject.__init__(self)
        self.id         = None
        self.status     = 'new'
        self.service    = service_name
        self.descr      = ''
        self.created    = datetime.utcnow()
        self.closed     = None
        self.progress   = .0
        self.created_by = getuser()
        self.xml        = etree.Element('order', service = self.service)

    def __repr__(self):
        return "<Order('%s','%s','%s')>" % (self.id, self.service, self.status)

    @staticmethod
    def from_etree(order_node):
        """
        Creates a new instance by parsing the given XML.

        @type  order_node: lxml.etree.Element
        @param order_node: The order node of an etree.
        @rtype:  Order
        @return: A new instance of an order.
        """
        # Parse required attributes.
        descr_node       = order_node.find('description')
        order_id         = order_node.get('id')
        order            = Order(order_node.get('service'))
        order.xml        = order_node
        order.id         = order_id is not None and int(order_id) or None
        order.status     = order_node.get('status',     order.status)
        order.created_by = order_node.get('created-by', order.created_by)
        created          = order_node.get('created')
        closed           = order_node.get('closed')
        progress         = order_node.get('progress')
        if descr_node is not None:
            order.descr = descr_node.text
        if created:
            created = created.split('.', 1)[0]
            created = datetime.strptime(created, "%Y-%m-%d %H:%M:%S")
            order.created = created
        if closed:
            closed = closed.split('.', 1)[0]
            closed = datetime.strptime(closed, "%Y-%m-%d %H:%M:%S")
            order.closed = closed
        if progress is not None:
            order.progress = float(progress)
        return order

    @staticmethod
    def from_xml(xml):
        """
        Creates a new instance by parsing the given XML.

        @type  xml: str
        @param xml: A string containing an XML formatted order.
        @rtype:  Order
        @return: A new instance of an order.
        """
        xml = etree.fromstring(xml)
        return Order.from_etree(xml.find('order'))

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
        xml = etree.parse(filename)
        return Order.from_etree(xml.find('order'))

    @staticmethod
    def from_csv_file(service, filename, encoding = 'utf-8'):
        """
        Creates a new instance by reading the given CSV file.

        @type  service: str
        @param service: The service name.
        @type  filename: str
        @param filename: A file containing a CSV formatted list of hosts.
        @type  encoding: str
        @param encoding: The name of the encoding.
        @rtype:  Order
        @return: A new instance of an order.
        """
        order = Order(service)
        hosts = get_hosts_from_csv(filename, encoding = encoding)
        add_hosts_to_etree(order.xml, hosts)
        return order

    def toetree(self):
        """
        Returns the order as an lxml etree.

        @rtype:  lxml.etree
        @return: The resulting tree.
        """
        if self.id:
            self.xml.attrib['id'] = str(self.id)
        if self.status:
            self.xml.attrib['status'] = str(self.status)
        if self.created:
            self.xml.attrib['created'] = str(self.created)
        if self.closed:
            self.xml.attrib['closed'] = str(self.closed)
        if self.progress:
            self.xml.attrib['progress'] = str(self.progress)
        if self.descr:
            etree.SubElement(self.xml, 'description').text = str(self.descr)
        if self.created_by:
            self.xml.attrib['created-by'] = str(self.created_by)
        return self.xml

    def toxml(self, pretty = True):
        """
        Returns the order as an XML formatted string.

        @type  pretty: bool
        @param pretty: Whether to format the XML in a human readable way.
        @rtype:  str
        @return: The XML representing the order.
        """
        xml   = etree.Element('xml')
        order = self.toetree()
        xml.append(order)
        return etree.tostring(xml, pretty_print = pretty)

    def todict(self):
        """
        Returns the order's attributes as one flat dictionary.

        @rtype:  dict
        @return: A dictionary representing the order.
        """
        values = dict(service     = self.get_service_name(),
                      status      = self.get_status(),
                      description = self.get_description(),
                      progress    = self.get_progress(),
                      created     = self.get_created_timestamp(),
                      closed      = self.get_closed_timestamp(),
                      created_by  = self.get_created_by())
        if self.id:
            values['id'] = self.get_id()
        return values

    def write(self, thefile):
        """
        Export the order as an XML file.

        @type  thefile: str or file object
        @param thefile: XML
        """
        if hasattr(thefile, 'write'):
            thefile.write(self.toxml())
            return

        dirname = os.path.dirname(thefile)
        with NamedTemporaryFile(dir    = dirname,
                                prefix = '.',
                                delete = False) as tmpfile:
            tmpfile.write(self.toxml())
            tmpfile.flush()
            os.chmod(tmpfile.name, 0644)
            os.rename(tmpfile.name, thefile)

    def is_valid(self):
        """
        Returns True if the order validates, False otherwise.

        @rtype:  bool
        @return: True if the order is valid, False otherwise.
        """
        return True #FIXME

    def get_id(self):
        """
        Returns the order id.

        @rtype:  str
        @return: The id of the order.
        """
        return self.id

    def set_service_name(self, name):
        """
        Set the name of the service that is ordered.

        @type  name: str
        @param name: The service name.
        """
        self.service = name

    def get_service_name(self):
        """
        Returns the name of the service that is ordered.

        @rtype:  str
        @return: The service name.
        """
        return self.service

    def get_status(self):
        """
        Returns the order status.

        @rtype:  str
        @return: The order status.
        """
        return self.status

    def set_description(self, description):
        """
        Sets a freely defined description on the order.

        @type  description: str
        @param description: The new description.
        """
        self.descr = description and str(description) or ''

    def get_description(self):
        """
        Returns the description of the order.

        @rtype:  str
        @return: The description.
        """
        return self.descr

    def get_created_timestamp(self):
        """
        Returns the time at which the order was created.

        @rtype:  datetime.datetime
        @return: The timestamp.
        """
        return self.created

    def get_closed_timestamp(self):
        """
        Returns the time at which the order was closed, or None if the
        order is still open.

        @rtype:  datetime.datetime|None
        @return: The timestamp or None.
        """
        return self.closed

    def get_created_by(self):
        """
        Returns the username of the user who opened the order. Defaults
        to whatever getpass.getuser() returns.

        @rtype:  str
        @return: The value of the 'created-by' field.
        """
        return self.created_by

    def get_progress(self):
        """
        Returns the progress of the order.

        @rtype:  float|None
        @return: The progress (1.0 is max).
        """
        return self.progress

    def get_progress_percent(self):
        """
        Returns the progress as a string, in percent.

        @rtype:  str
        @return: The progress in percent.
        """
        return '%.1f' % (self.progress * 100.0)

    def close(self):
        """
        Marks the order closed.
        """
        self.closed = datetime.utcnow()
