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
import os, time, cgi, logging
from traceback               import format_exc
from HTTPDigestServer        import HTTPRequestHandler, HTTPServer
from lxml                    import etree
from urlparse                import parse_qs
from Daemon                  import Daemon
from Order                   import Order
from Exscript                import Host
from Exscript.util.decorator import bind

"""
URL list:

  Path                            Method  Function
  order/                          POST    Place an XML formatted order
  order/list/?offset=10&limit=25  GET     Get a list of orders
  order/full/?id=1234             GET     Get the XML formatted order 1234
  order/status/?id=1234           GET     Get the status for order 1234
  order/status/?id=1234&task=55   GET     Get the status for host 55 in order 1234
  services/                       GET     Service overview   (not implemented)
  services/foo/                   GET     Get info for the "foo" service   (not implemented)

To test with curl:

  curl --digest --user exscript-rest:exscript-rest --data @postorder localhost:8123/order/
"""

class HTTPHandler(HTTPRequestHandler):
    def get_response(self):
        data = parse_qs(self.data)
        if self.path == '/order/':
            self.daemon.logger.debug('Parsing order from REST request.')
            order = Order.from_xml(data['xml'][0])
            self.daemon.logger.debug('XML order parsed complete.')
            self.daemon._place_order(order)
            return str(order.get_id())
        elif self.path == '/order/status/':
            order = self.daemon.get_order_from_id(str(self.args['id']))
            if not order:
                raise Exception('no such order id')
            return order.status
        else:
            raise Exception('no such API call')

    def handle_POST(self):
        self.daemon = self.server.user_data
        self.daemon.logger.debug('Receiving REST request.')
        try:
            response = self.get_response()
        except Exception, e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(format_exc().encode('utf8'))
            self.daemon.logger.error('Exception: %s' % e)
        else:
            self.daemon.logger.debug('Sending REST response.')
            self.wfile.write(response)
        self.daemon.logger.debug('REST call complete.')

    def handle_GET(self):
        self.handle_POST()

class RestDaemon(Daemon):
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
        self.logger.info('REST daemon "' + self.name + '" running on ' + address)
        try:
            print 'Daemon', repr(self.name), 'listening on', repr(address) + '.'
            self.server.serve_forever()
        except KeyboardInterrupt:
            print '^C received, shutting down server'
            self.logger.info('Shutting down normally.')
            self.server.socket.close()
