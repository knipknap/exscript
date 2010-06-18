import os, time, cgi
from HTTPDigestServer        import HTTPRequestHandler, HTTPServer
from lxml                    import etree
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
"""

class HTTPHandler(HTTPRequestHandler):
    def handle_POST(self):
        if self.path == '/order/':
            print "ORDER POSTED", self.data
            self.wfile.write("<html>FIXME</html>")
            return
        raise Exception('no such API call')

class RestDaemon(Daemon):
    def __init__(self,
                 name,
                 address    = '',
                 port       = 80,
                 database   = None,
                 processors = None):
        Daemon.__init__(self, name, database, processors)
        self.address = address
        self.port    = port
        self.server  = HTTPServer((self.address, self.port), HTTPHandler)

    def add_account(self, account):
        user     = account.get_name()
        password = account.get_password()
        self.server.accounts[user] = password

    def run(self):
        address = self.address + ':' + str(self.port)
        print 'REST daemon "' + self.name + '" running on ' + address
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            print '^C received, shutting down server'
            self.server.socket.close()
