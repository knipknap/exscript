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
from traceback                  import format_exc
from urlparse                   import parse_qs
from lxml                       import etree
from Exscript                   import Host
from Exscriptd.HTTPDigestServer import HTTPRequestHandler, HTTPServer
from Exscriptd.Daemon           import Daemon
from Exscriptd.Order            import Order

"""
URL list:

  Path                            Method  Function
  order/                          POST    Place an XML formatted order
  order/get/?id=1234              GET     Returns order 1234
  order/status/?id=1234           GET     Status and progress for order 1234
  order/count/                    GET     Get the total number of orders
  order/list/?offset=10&limit=25  GET     Get a list of orders
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

class HTTPHandler(HTTPRequestHandler):
    def get_response(self):
        data = parse_qs(self.data)
        if self.path == '/order/':
            self.daemon.logger.debug('Parsing order from HTTP request.')
            order = Order.from_xml(data['xml'][0])
            self.daemon.logger.debug('XML order parsed complete.')
            self.daemon._place_order(order)
            return str(order.get_id())
        elif self.path == '/order/get/':
            id    = int(self.args.get('id'))
            order = self.daemon.get_order_from_id(id)
            return order.toxml()
        elif self.path == '/order/count/':
            return str(self.daemon.count_orders())
        elif self.path == '/order/status/':
            order_id = int(self.args['id'])
            order    = self.daemon.get_order_from_id(order_id)
            progress = self.daemon.get_order_progress_from_id(order_id)
            if not order:
                raise Exception('no such order id')
            closed = order.get_closed_timestamp()
            if closed is not None:
                closed = str(closed)
            response = {'status':   order.status,
                        'progress': progress,
                        'closed':   closed}
            return 'application/json', json.dumps(response)
        elif self.path == '/order/list/':
            # Fetch the orders.
            offset = int(self.args.get('offset', 0))
            limit  = min(100, int(self.args.get('limit', 100)))
            orders = self.daemon.get_order_list(offset = offset, limit = limit)

            # Assemble an XML document containing the orders.
            xml = etree.Element('xml')
            for order in orders:
                xml.append(order.toetree())
            return etree.tostring(xml, pretty_print = True)
        elif self.path == '/task/get/':
            id   = int(self.args.get('id'))
            task = self.daemon.get_task_from_id(id)
            return task.toxml()
        elif self.path == '/task/count/':
            order_id = self.args.get('order_id')
            if order_id:
                n_tasks = self.daemon.count_tasks(int(order_id))
            else:
                n_tasks = self.daemon.count_tasks()
            return 'application/json', json.dumps(n_tasks)
        elif self.path == '/task/list/':
            # Fetch the tasks.
            order_id = int(self.args.get('order_id'))
            offset   = int(self.args.get('offset', 0))
            limit    = min(100, int(self.args.get('limit', 100)))
            tasks    = self.daemon.get_task_list(order_id,
                                                 offset = offset,
                                                 limit = limit)

            # Assemble an XML document containing the orders.
            xml = etree.Element('xml')
            for task in tasks:
                xml.append(task.toetree())
            return etree.tostring(xml, pretty_print = True)
        elif self.path == '/log/':
            task_id  = int(self.args.get('task_id'))
            task     = self.daemon.get_task_from_id(task_id)
            filename = task.get_logfile()
            if filename and os.path.isfile(filename):
                with open(filename) as file:
                    return file.read()
            else:
                return ''
        elif self.path == '/trace/':
            task_id  = int(self.args.get('task_id'))
            task     = self.daemon.get_task_from_id(task_id)
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

class HTTPDaemon(Daemon):
    def __init__(self,
                 name,
                 address    = '',
                 port       = 80,
                 database   = None,
                 processors = None,
                 logdir     = None):
        Daemon.__init__(self, name, database, processors, logdir)
        self.address = address
        self.port    = port
        addr         = self.address, self.port
        self.server  = HTTPServer(addr, HTTPHandler, self)

    def add_account(self, account):
        user     = account.get_name()
        password = account.get_password()
        self.server.accounts[user] = password

    def run(self):
        address = self.address + ':' + str(self.port)
        self.logger.info('HTTP daemon "' + self.name + '" starting on ' + address)
        self.close_open_orders()
        try:
            print 'Daemon', repr(self.name), 'listening on', repr(address) + '.'
            self.server.serve_forever()
        except KeyboardInterrupt:
            print '^C received, shutting down server'
            self.logger.info('Shutting down normally.')
            self.server.socket.close()
