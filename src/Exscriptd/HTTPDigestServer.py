"""
Copyright (c) 2006, 2007 Andre Roberge and Johannes Woolard
              2010 Samuel Abels (removed Crunchy dependencies)

Permission is hereby granted, free of charge, to any person 
obtaining a copy of this software and associated documentation 
files (the "Software"), to deal in the Software without restriction, 
including without limitation the rights to use, copy, modify, merge, 
publish, distribute, sublicense, and/or sell copies of the Software, 
and to permit persons to whom the Software is furnished to do so, 
subject to the following conditions:

The above copyright notice and this permission notice shall be 
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, 
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF 
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND 
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS 
BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN 
ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN 
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE 
SOFTWARE.
"""
"""
serve HTTP in a beautiful threaded way, allowing requests to branch
off into new threads and handling URLs automagically
This was built for Crunchy - and it rocks!
In some ways it is more restrictive than the default python HTTPserver -
for instance, it can only handle GET and POST requests and actually
treats them the same.
"""

import base64
import email
import email.message
import sys
import time
import urllib
from BaseHTTPServer import BaseHTTPRequestHandler
from BaseHTTPServer import HTTPServer as PyHTTPServer

python_version = sys.version_info[0] + sys.version_info[1]/10.0

if sys.version_info < (2, 6):
    from cgi import parse_qs
else:
    from urlparse import parse_qs
from SocketServer import ThreadingMixIn, TCPServer
from urlparse import urlparse
from traceback import format_exc

# Selective imports only for urllib2 because 2to3 will not replace the
# urllib2.<method> calls below. Also, 2to3 will throw an error if we
# try to do a from _ import _.
if sys.version_info[0] < 3:
    import urllib2
    parse_http_list = urllib2.parse_http_list
    parse_keqv_list = urllib2.parse_keqv_list
else:
    from urllib.request import parse_http_list, parse_keqv_list

DEBUG = False

realm = "Crunchy Access"

# This is convoluted because there's no way to tell 2to3 to insert a
# byte literal.
HEADER_NEWLINES = [x.encode('ascii') for x in (u'\r\n', u'\n', u'')]

if python_version < 2.5:
    import md5
    def md5hex(x):
        return md5.md5(x).hexdigest()
else:
    import hashlib
    def md5hex(x):
        return hashlib.md5(x).hexdigest()

def require_authenticate(func):
    '''A decorator to add digest authorization checks to HTTP Request Handlers'''

    def wrapped(self):
        if not hasattr(self, 'authenticated'):
            self.authenticated = None

        auth = self.headers.get(u'Authorization')
        if not self.authenticated and auth is not None:
            token, fields = auth.split(' ', 1)
            if token == 'Digest':
                cred = parse_http_list(fields)
                cred = parse_keqv_list(cred)

                # The request must contain all these keys to
                # constitute a valid response.
                keys = u'realm username nonce uri response'.split()
                if not all(cred.get(key) for key in keys):
                    self.authenticated = False
                elif cred['realm'] != realm \
                  or cred['username'] not in self.server.accounts:
                    self.authenticated = False
                elif 'qop' in cred and ('nc' not in cred or 'cnonce' not in cred):
                    self.authenticated = False
                else:
                    location = u'%s:%s' % (self.command, self.path)
                    location = location.encode('utf8')
                    location = md5hex(location)
                    password = self.server.get_password(cred['username'])
                    if 'qop' in cred:
                        info = (cred['nonce'],
                                cred['nc'],
                                cred['cnonce'],
                                cred['qop'],
                                location)
                    else:
                        info = cred['nonce'], location

                    expect = u'%s:%s' % (password, ':'.join(info))
                    expect = md5hex(expect.encode('utf8'))
                    self.authenticated = (expect == cred['response'])
                    if self.authenticated:
                        self.crunchy_username = cred['username']

        if self.authenticated is None:
            msg = u"You are not allowed to access this page. Please login first!"
        elif self.authenticated is False:
            msg = u"Authenticated Failed"
        if not self.authenticated :
            self.send_response(401)
            nonce = (u"%d:%s" % (time.time(), realm)).encode('utf8')
            self.send_header('WWW-Authenticate',
                             'Digest realm="%s",'
                             'qop="auth",'
                             'algorithm="MD5",'
                             'nonce="%s"' % (realm, nonce))
            self.end_headers()
            self.wfile.write(msg.encode('utf8'))
        else:
            return func(self)

    return wrapped


class HTTPServer(ThreadingMixIn, PyHTTPServer):
    daemon_threads = True
    accounts = {}

    def __init__(self, addr, rqh):
        self.default_handler = None
        self.handler_table = {}
        PyHTTPServer.__init__(self, addr, rqh)

    def register_default_handler(self, handler):
        """register a default handler"""
        self.default_handler = handler

    def register_handler(self, path, handler):
        """
        register a handler function
        the function should be of the form: handler(request)
        """
        self.handler_table[path] = handler

    def register_handler_instance(self, handlerinstance):
        """register a handler class instance,
        the instance functions should be of the form: class.handler(self, request)
        and should have as their docstring the path they want to handle
        """
        pass

    def get_password(self, username):
        plain = self.accounts.get(username)
        if not plain:
            return None
        return md5hex('%s:%s:%s' % (username, realm, plain))

    def get_handler(self, path):
        """returns none if no handler registered"""
        if DEBUG:
            print("entering get_handler")
        if path in self.handler_table:
            if DEBUG:
                print("path %s in self.handler_table."%path)
                print("self.handler_table[path] = %s" % self.handler_table[path])
            return self.handler_table[path]
        else:
            if DEBUG:
                print("path %s NOT in self.handler_table."%path)
            return self.default_handler

def parse_headers(fp, _class=email.message.Message):
    """Parses only RFC2822 headers from a file pointer.

    This code is taken directly from the Python 3 stdlib, adapted for
    2to3. Returns a dictionary of unicode strings mapping to unicode
    strings.
    """
    headers = []
    while True:
        line = fp.readline()
        headers.append(line)
        if line in HEADER_NEWLINES:
            break

    hbytes = u''.encode('ascii').join(headers)

    # It turns out that in Python 3, email.Parser requires Unicode.
    # Unfortunately,in Python 2, email.Parser refuses to handle
    # Unicode and returns an empty object. We have to make sure that
    # parse_headers returns Unicode in both Python 2 and Python 3. The
    # easiest way is to throw away the email.message.Message interface
    # and just return a dict instead, which lets us massage the bytes
    # into Unicode.

    # iso-8559-1 encoding taken from http/client.py, where this
    # function was stolen from.
    E = 'iso-8859-1'

    if sys.version_info[0] < 3:
        items = email.message_from_string(hbytes).items()
        return dict((k.decode(E), v.decode(E)) for k, v in items)

    hstring = hbytes.decode(E)
    return dict(email.message_from_string(hstring))

def parse_url(path):
    """Given a urlencoded path, returns the path and the dictionary of
    query arguments, all in Unicode."""

    # path changes from bytes to Unicode in going from Python 2 to
    # Python 3.
    if sys.version_info[0] < 3:
        o = urlparse(urllib.unquote_plus(path).decode('utf8'))
    else:
        o = urlparse(urllib.unquote_plus(path))

    path = o.path
    args = {}

    # Convert parse_qs' str --> [str] dictionary to a str --> str
    # dictionary since we never use multi-value GET arguments
    # anyway.
    multiargs = parse_qs(o.query, keep_blank_values=True)
    for arg, value in multiargs.items():
        args[arg] = value[0]

    return path, args

def message_wrapper(self, fp, irrelevant):
    return parse_headers(fp)

class HTTPRequestHandler(BaseHTTPRequestHandler):
    # In Python 3, BaseHTTPRequestHandler went from using the
    # deprecated mimetools.Message class to the new
    # email.message.Message class for self.headers. Unfortunately, the
    # two APIs are not compatible. Fortunately, there's an API in
    # place to fiddle with the class that's chosen. Here we force
    # Python 2 to adopt email.message.Message.
    if sys.version_info[0] < 3:
        MessageClass = message_wrapper

    @require_authenticate
    def do_POST(self):
        """handle an HTTP request"""
        # at first, assume that the given path is the actual path and there are no arguments
        if DEBUG:
            print(self.path)

        self.path, self.args = parse_url(self.path)

        # Extract POST data, if any. Clumsy syntax due to Python 2 and
        # 2to3's lack of a byte literal.
        self.data = u"".encode()
        length = self.headers.get('Content-Length')
        if length and length.isdigit():
            self.data = self.rfile.read(int(length))

        # POST data gets automatically decoded into Unicode because
        # much of Crunchy's code assumes this. The bytestring will
        # still be available in the bdata attribute.
        self.bdata = self.data
        try:
            self.data = self.data.decode('utf8')
        except UnicodeDecodeError:
            self.data = None

        # Run the handler.
        if DEBUG:
            print(u"Preparing to call get_handler in do_POST")
        try:
            self.handle_response()
        except:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(format_exc().encode('utf8'))

    # We draw no distinction.
    do_GET = do_POST

    def handle_response(self):
        self.send_response(404)
        self.end_headers()
        self.wfile.write('not found'.encode('utf8'))

    def send_response(self, code):
        BaseHTTPRequestHandler.send_response(self, code)
        self.send_header("Connection", "close")

if __name__ == '__main__':
    try:
        server = HTTPServer(('', 8123), HTTPRequestHandler)
        server.accounts['test'] = 'fo'
        print 'started httpserver...'
        server.serve_forever()
    except KeyboardInterrupt:
        print '^C received, shutting down server'
        server.socket.close()
