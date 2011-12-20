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
import os
import json
import logging
from traceback import format_exc
from urlparse import parse_qs
from lxml import etree
from Exscript import Host
from Exscript.servers.HTTPd import HTTPd, RequestHandler
from Exscript.util.event import Event
from Exscriptd.Order import Order

"""
URL list:

  Path                            Method  Function
  order/                          POST    Place an XML formatted order
  order/get/?id=1234              GET     Returns order 1234
  order/status/?id=1234           GET     Status and progress for order 1234
  order/count/                    GET     Get the total number of orders
  order/count/?service=grabber    GET     Number of orders matching the name
  order/list/?offset=10&limit=25  GET     Get a list of orders
  order/list/?service=grabber     GET     Filter list of orders by service name
  order/list/?description=foobar  GET     Filter list of orders by description
  order/list/?status=completed    GET     Filter list of orders by status
  task/get/?id=1234               GET     Returns task 1234
  task/count/?order_id=1234       GET     Get the number of tasks for order 1234
  task/list/?order_id=1234        GET     Get a list of tasks for order 1234
  log/?task_id=4567               GET     Returns the content of the logfile
  trace/?task_id=4567             GET     Returns the content of the trace file
  services/                       GET     Service overview   (not implemented)
  services/foo/                   GET     Get info for the "foo" service   (not implemented)

To test with curl:

  curl --digest --user exscript-http:exscript-http --data @postorder localhost:8123/order/
"""

class HTTPHandler(RequestHandler):
    def get_response(self):
        data     = parse_qs(self.data)
        logger   = self.daemon.logger
        order_db = self.daemon.parent.get_order_db()

        if self.path == '/order/':
            logger.debug('Parsing order from HTTP request.')
            order = Order.from_xml(data['xml'][0])
            logger.debug('XML order parsed complete.')
            self.daemon.order_incoming_event(order)
            return 'application/json', json.dumps(order.get_id())

        elif self.path == '/order/get/':
            id    = int(self.args.get('id'))
            order = order_db.get_order(id = id)
            return order.toxml()

        elif self.path == '/order/count/':
            order_id   = self.args.get('order_id')
            service    = self.args.get('service')
            descr      = self.args.get('description')
            status     = self.args.get('status')
            created_by = self.args.get('created_by')
            n_orders   = order_db.count_orders(id          = order_id,
                                               service     = service,
                                               description = descr,
                                               status      = status,
                                               created_by  = created_by)
            return 'application/json', json.dumps(n_orders)

        elif self.path == '/order/status/':
            order_id = int(self.args['id'])
            order    = order_db.get_order(id = order_id)
            progress = order_db.get_order_progress_from_id(order_id)
            if not order:
                raise Exception('no such order id')
            closed = order.get_closed_timestamp()
            if closed is not None:
                closed = str(closed)
            response = {'status':   order.get_status(),
                        'progress': progress,
                        'closed':   closed}
            return 'application/json', json.dumps(response)

        elif self.path == '/order/list/':
            # Fetch the orders.
            offset     = int(self.args.get('offset', 0))
            limit      = min(100, int(self.args.get('limit', 100)))
            order_id   = self.args.get('order_id')
            service    = self.args.get('service')
            descr      = self.args.get('description')
            status     = self.args.get('status')
            created_by = self.args.get('created_by')
            orders     = order_db.get_orders(id          = order_id,
                                             service     = service,
                                             description = descr,
                                             status      = status,
                                             created_by  = created_by,
                                             offset      = offset,
                                             limit       = limit)

            # Assemble an XML document containing the orders.
            xml = etree.Element('xml')
            for order in orders:
                xml.append(order.toetree())
            return etree.tostring(xml, pretty_print = True)

        elif self.path == '/task/get/':
            id   = int(self.args.get('id'))
            task = order_db.get_task(id = id)
            return task.toxml()

        elif self.path == '/task/count/':
            order_id = self.args.get('order_id')
            if order_id:
                n_tasks = order_db.count_tasks(order_id = int(order_id))
            else:
                n_tasks = order_db.count_tasks()
            return 'application/json', json.dumps(n_tasks)

        elif self.path == '/task/list/':
            # Fetch the tasks.
            order_id = int(self.args.get('order_id'))
            offset   = int(self.args.get('offset', 0))
            limit    = min(100, int(self.args.get('limit', 100)))
            tasks    = order_db.get_tasks(order_id = order_id,
                                          offset   = offset,
                                          limit    = limit)

            # Assemble an XML document containing the orders.
            xml = etree.Element('xml')
            for task in tasks:
                xml.append(task.toetree())
            return etree.tostring(xml, pretty_print = True)

        elif self.path == '/log/':
            task_id  = int(self.args.get('task_id'))
            task     = order_db.get_task(id = task_id)
            filename = task.get_logfile()
            if filename and os.path.isfile(filename):
                with open(filename) as file:
                    return file.read()
            else:
                return ''

        elif self.path == '/trace/':
            task_id  = int(self.args.get('task_id'))
            task     = order_db.get_task(id = task_id)
            filename = task.get_tracefile()
            if filename and os.path.isfile(filename):
                with open(filename) as file:
                    return file.read()
            else:
                return ''

        else:
            raise Exception('no such API call')

    def handle_POST(self):
        self.daemon = self.server.user_data
        self.daemon.logger.debug('Receiving HTTP request.')
        try:
            response = self.get_response()
        except Exception, e:
            tb = format_exc()
            print tb
            self.send_response(500)
            self.end_headers()
            self.wfile.write(tb.encode('utf8'))
            self.daemon.logger.error('Exception: %s' % tb)
        else:
            self.send_response(200)
            try:
                mime_type, response = response
            except ValueError:
                self.daemon.logger.debug('Sending HTTP/text response.')
            else:
                self.daemon.logger.debug('Sending HTTP/json response.')
                self.send_header('Content-type', mime_type)
            self.end_headers()
            self.wfile.write(response)
        self.daemon.logger.debug('HTTP call complete.')

    def handle_GET(self):
        self.handle_POST()

    def log_message(self, format, *args):
        daemon = self.server.user_data
        daemon.logger.info(self.address_string() + ' - ' + format % args)

class HTTPDaemon(object):
    def __init__(self,
                 parent,
                 name,
                 logger,
                 address = '',
                 port    = 80):
        self.parent               = parent
        self.name                 = name
        self.logger               = logger
        self.order_incoming_event = Event()
        self.address              = address
        self.port                 = port
        addr                      = self.address, self.port
        self.server               = HTTPd(addr, HTTPHandler, self)
        self.parent.daemon_added(self)

    def log(self, order, message, level = logging.INFO):
        msg = '%s/%s/%s: %s' % (self.name,
                                order.get_service_name(),
                                order.get_id(),
                                message)
        self.logger.log(level, msg)

    def add_account(self, account):
        user     = account.get_name()
        password = account.get_password()
        self.server.add_account(user, password)

    def run(self):
        address  = (self.address or '*') + ':' + str(self.port)
        nameaddr = self.name, address
        self.logger.info('HTTPDaemon %s/%s starting.' % nameaddr)
        try:
            self.logger.info('HTTPDaemon %s/%s listening' % nameaddr)
            self.server.serve_forever()
        except KeyboardInterrupt:
            print '^C received, shutting down server'
            self.logger.info('Shutting down normally.')
            self.server.socket.close()
