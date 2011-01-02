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
import json
from datetime         import datetime
from lxml             import etree
from urllib           import urlencode
from urllib2          import HTTPDigestAuthHandler, build_opener, HTTPError
from HTTPDigestServer import realm
from Order            import Order
from Task             import Task

class Client(object):
    """
    An Exscriptd client that communicates via HTTP.
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
            if hasattr(e, 'read'):
                raise Exception(str(e) + ' with ' + e.read())
            else:
                raise Exception(str(e))
        if result.getcode() != 200:
            raise Exception(result.read())
        order.id = int(result.read())

    def get_order_from_id(self, id):
        """
        Returns the order with the given id.

        @type  id: str
        @param id: The id of the order.
        @rtype:  Order
        @return: The order if it exists, None otherwise.
        """
        args   = 'id=%d' % id
        url    = self.address + '/order/get/?' + args
        result = self.opener.open(url)
        if result.getcode() != 200:
            raise Exception(response)
        return Order.from_xml(result.read())

    def get_order_status_from_id(self, order_id):
        """
        Returns a tuple containing the status of the order with the given
        id if it exists. Raises an exception otherwise. The tuple contains
        the following elements::

            status, progress, closed

        where 'status' is a human readable string, progress is a
        floating point number between 0.0 and 1.0, and closed is the
        time at which the order was closed.

        @type  order_id: str
        @param order_id: The id of the order.
        @rtype:  (str, float, datetime.timestamp)
        @return: The status and progress of the order.
        """
        url      = self.address + '/order/status/?id=%s' % order_id
        result   = self.opener.open(url)
        response = result.read()
        if result.getcode() != 200:
            raise Exception(response)
        data   = json.loads(response)
        closed = data['closed']
        if closed is not None:
            closed = closed.split('.', 1)[0]
            closed = datetime.strptime(closed, "%Y-%m-%d %H:%M:%S")
        return data['status'], data['progress'], closed

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

    def get_order_list(self, offset = 0, limit = 0):
        """
        Returns a list of currently running orders.

        @type  offset: int
        @param offset: The number of orders to skip.
        @type  limit: int
        @param limit: The maximum number of orders to return.
        @rtype:  list[Order]
        @return: A list of orders.
        """
        args   = 'offset=%d&limit=%d' % (offset, limit)
        url    = self.address + '/order/list/?' + args
        result = self.opener.open(url)
        if result.getcode() != 200:
            raise Exception(response)
        xml = etree.parse(result)
        return [Order.from_etree(n) for n in xml.iterfind('order')]

    def count_tasks(self, order_id = None):
        """
        Returns the total number of tasks.

        @rtype:  int
        @return: The number of tasks.
        """
        args = ''
        if order_id:
            args += '?order_id=%d' % order_id
        url      = self.address + '/task/count/' + args
        result   = self.opener.open(url)
        response = result.read()
        if result.getcode() != 200:
            raise Exception(response)
        return int(response)

    def get_task_list(self, order_id, offset = 0, limit = 0):
        """
        Returns a list of currently running orders.

        @type  offset: int
        @param offset: The number of orders to skip.
        @type  limit: int
        @param limit: The maximum number of orders to return.
        @rtype:  list[Order]
        @return: A list of orders.
        """
        args   = 'order_id=%d&offset=%d&limit=%d' % (order_id, offset, limit)
        url    = self.address + '/task/list/?' + args
        result = self.opener.open(url)
        if result.getcode() != 200:
            raise Exception(response)
        xml = etree.parse(result)
        return [Task.from_etree(n) for n in xml.iterfind('task')]

    def get_task_from_id(self, id):
        """
        Returns the task with the given id.

        @type  id: int
        @param id: The id of the task.
        @rtype:  Task
        @return: The task with the given id.
        """
        args   = 'id=%d' % id
        url    = self.address + '/task/get/?' + args
        result = self.opener.open(url)
        if result.getcode() != 200:
            raise Exception(response)
        return Task.from_xml(result.read())

    def get_log_from_task_id(self, task_id):
        """
        Returns the content of the logfile for the given task.

        @type  task_id: int
        @param task_id: The task id.
        @rtype:  str
        @return: The file content.
        """
        args   = 'task_id=%d' % task_id
        url    = self.address + '/log/?' + args
        result = self.opener.open(url)
        if result.getcode() != 200:
            raise Exception(response)
        return result.read()

    def get_trace_from_task_id(self, task_id):
        """
        Returns the content of the trace file for the given task.

        @type  task_id: int
        @param task_id: The task id.
        @rtype:  str
        @return: The file content.
        """
        args   = 'task_id=%d' % task_id
        url    = self.address + '/trace/?' + args
        result = self.opener.open(url)
        if result.getcode() != 200:
            raise Exception(response)
        return result.read()
