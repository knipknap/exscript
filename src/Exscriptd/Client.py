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
#HACK: the return value of opener.open(url) does not support
# __enter__ and __exit__ for Python's "with" in older versions
# of Python.
import urllib
urllib.addinfourl.__enter__ = lambda x: x
urllib.addinfourl.__exit__ = lambda s, *x: s.close()
#END HACK
from datetime import datetime
from urllib import urlencode
from urllib2 import HTTPDigestAuthHandler, build_opener, HTTPError
from lxml import etree
from Exscript.servers.HTTPd import default_realm
from Exscriptd.Order import Order
from Exscriptd.Task import Task

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
        self.handler.add_password(realm  = default_realm,
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
            with self.opener.open(url, data) as result:
                if result.getcode() != 200:
                    raise Exception(result.read())
                order.id = json.loads(result.read())
        except HTTPError, e:
            if hasattr(e, 'read'):
                raise Exception(str(e) + ' with ' + e.read())
            else:
                raise Exception(str(e))

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
        with self.opener.open(url) as result:
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
        url = self.address + '/order/status/?id=%s' % order_id
        with self.opener.open(url) as result:
            response = result.read()
            if result.getcode() != 200:
                raise Exception(response)
        data   = json.loads(response)
        closed = data['closed']
        if closed is not None:
            closed = closed.split('.', 1)[0]
            closed = datetime.strptime(closed, "%Y-%m-%d %H:%M:%S")
        return data['status'], data['progress'], closed

    def count_orders(self,
                     order_id    = None,
                     service     = None,
                     description = None,
                     status      = None,
                     created_by  = None):
        """
        Returns the total number of orders.

        @rtype:  int
        @return: The number of orders.
        @type  kwargs: dict
        @param kwargs: See L{get_order_list()}
        """
        args = {}
        if order_id:
            args['order_id'] = order_id
        if service:
            args['service'] = service
        if description:
            args['description'] = description
        if status:
            args['status'] = status
        if created_by:
            args['created_by'] = created_by
        url = self.address + '/order/count/?' + urlencode(args)
        with self.opener.open(url) as result:
            response = result.read()
            if result.getcode() != 200:
                raise Exception(response)
        return json.loads(response)

    def get_order_list(self,
                       order_id    = None,
                       service     = None,
                       description = None,
                       status      = None,
                       created_by  = None,
                       offset      = 0,
                       limit       = 0):
        """
        Returns a list of currently running orders.

        @type  offset: int
        @param offset: The number of orders to skip.
        @type  limit: int
        @param limit: The maximum number of orders to return.
        @type  kwargs: dict
        @param kwargs: The following keys may be used:
                         - order_id - the order id (str)
                         - service - the service name (str)
                         - description - the order description (str)
                         - status - the status (str)
                         - created_by - the user name (str)
        @rtype:  list[Order]
        @return: A list of orders.
        """
        args = {'offset': offset, 'limit': limit}
        if order_id:
            args['order_id'] = order_id
        if service:
            args['service'] = service
        if description:
            args['description'] = description
        if status:
            args['status'] = status
        if created_by:
            args['created_by'] = created_by
        url = self.address + '/order/list/?' + urlencode(args)
        with self.opener.open(url) as result:
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
        url = self.address + '/task/count/' + args
        with self.opener.open(url) as result:
            response = result.read()
            if result.getcode() != 200:
                raise Exception(response)
        return json.loads(response)

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
        args = 'order_id=%d&offset=%d&limit=%d' % (order_id, offset, limit)
        url  = self.address + '/task/list/?' + args
        with self.opener.open(url) as result:
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
        args = 'id=%d' % id
        url  = self.address + '/task/get/?' + args
        with self.opener.open(url) as result:
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
        args = 'task_id=%d' % task_id
        url  = self.address + '/log/?' + args
        with self.opener.open(url) as result:
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
        args = 'task_id=%d' % task_id
        url  = self.address + '/trace/?' + args
        with self.opener.open(url) as result:
            if result.getcode() != 200:
                raise Exception(response)
            return result.read()
