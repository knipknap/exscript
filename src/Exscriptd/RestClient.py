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
Places orders and requests the status from a server.
"""
from lxml             import etree
from urllib           import urlencode
from urllib2          import HTTPDigestAuthHandler, build_opener, HTTPError
from HTTPDigestServer import realm
from Order            import Order

class RestClient(object):
    """
    Handles all contact with a server.
    """

    def __init__(self, address, user, password):
        """
        Constructor. Any operations performed with an
        instance of a client are directed to the server with the
        given address, using the given login data.

        @type  address: str
        @param address: The base url of the server.
        @type  user: str
        @param user: The login name on the server.
        @type  password: str
        @param password: The password of the user.
        """
        self.address = 'http://' + address
        self.handler = HTTPDigestAuthHandler()
        self.opener  = build_opener(self.handler)
        self.handler.add_password(realm  = realm,
                                  uri    = self.address,
                                  user   = user,
                                  passwd = password)

    def place_order(self, order):
        """
        Sends the given order to the server, and updates the status
        of the order accordingly.

        @type  order: Order
        @param order: The order that is placed.
        """
        if order.status != 'new':
            msg = 'order status is "%s", should be "new"' % order.status
            raise ValueError(msg)
        if not order.is_valid():
            raise ValueError('incomplete or invalid order')

        order.status = 'accepted'
        url          = self.address + '/order/'
        xml          = order.toxml()
        data         = urlencode({'xml': xml})
        try:
            result = self.opener.open(url, data)
        except HTTPError, e:
            raise Exception(str(e) + ' with ' + e.read())
        if result.getcode() != 200:
            raise Exception(result.read())
        order.id = int(result.read())

    def get_order_from_id(self, order_id):
        """
        Returns the order with the given id.

        @type  order_id: str
        @param order_id: The id of the order.
        @rtype:  Order
        @return: The order if it exists, None otherwise.
        """
        raise NotImplementedError()

    def get_order_status_from_id(self, order_id):
        """
        Returns the status of the order with the given id if it
        exists. Returns 'not-found' otherwise.

        @type  order_id: str
        @param order_id: The id of the order.
        @rtype:  str
        @return: The status of the order.
        """
        url      = self.address + '/order/status/?id=%s' % order_id
        result   = self.opener.open(url)
        response = result.read()
        if result.getcode() != 200:
            raise Exception(response)
        return response

    def count_orders(self):
        """
        Returns the total number of orders.

        @rtype:  int
        @return: The number of orders.
        """
        url      = self.address + '/order/count/'
        result   = self.opener.open(url)
        response = result.read()
        if result.getcode() != 200:
            raise Exception(response)
        return int(response)

    def get_order_list(self, offset = 0, limit = 0, recursive = True):
        """
        Returns a list of currently running orders.

        @type  offset: int
        @param offset: The number of orders to skip.
        @type  limit: int
        @param limit: The maximum number of orders to return.
        @type  recursive: bool
        @param recursive: Whether to load the attached hosts.
        @rtype:  list[Order]
        @return: A list of orders.
        """
        args   = 'offset=%d&limit=%d' % (offset, limit)
        args  += '&recursive=%d' % (recursive and 1 or 0)
        url    = self.address + '/order/list/?' + args
        result = self.opener.open(url)
        if result.getcode() != 200:
            raise Exception(response)
        xml = etree.parse(result)
        return [Order.from_etree(n) for n in xml.iterfind('order')]
