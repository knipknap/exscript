import os, time, cgi
from HTTPDigestServer        import HTTPRequestHandler, HTTPServer
from lxml                    import etree
from Daemon                  import Daemon
from Order                   import Order
from Exscript                import Host
from Exscript.util.decorator import bind

class HTTPHandler(HTTPRequestHandler):
    def handle_response(self):
        self.wfile.write("<html>It works!</html>")

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
