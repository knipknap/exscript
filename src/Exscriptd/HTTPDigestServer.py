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

import email
import email.message
import sys
import time
import urllib
from urlparse import urlparse
from traceback import format_exc
from BaseHTTPServer import BaseHTTPRequestHandler
from BaseHTTPServer import HTTPServer as PyHTTPServer
from SocketServer import ThreadingMixIn

_python_version = sys.version_info[0] + sys.version_info[1]/10.0
default_realm = 'exscript'

if sys.version_info < (2, 6):
    from cgi import parse_qs
else:
    from urlparse import parse_qs

# Selective imports only for urllib2 because 2to3 will not replace the
# urllib2.<method> calls below. Also, 2to3 will throw an error if we
# try to do a from _ import _.
if sys.version_info[0] < 3:
    import urllib2
    parse_http_list = urllib2.parse_http_list
    parse_keqv_list = urllib2.parse_keqv_list
else:
    from urllib.request import parse_http_list, parse_keqv_list

# This is convoluted because there's no way to tell 2to3 to insert a
# byte literal.
HEADER_NEWLINES = [x.encode('ascii') for x in (u'\r\n', u'\n', u'')]

if _python_version < 2.5:
    import md5
    def md5hex(x):
        return md5.md5(x).hexdigest()
else:
    import hashlib
    def md5hex(x):
        return hashlib.md5(x).hexdigest()

def _error_401(handler, msg):
    handler.send_response(401)
    realm = handler.server.realm
    nonce = (u"%d:%s" % (time.time(), realm)).encode('utf8')
    handler.send_header('WWW-Authenticate',
                        'Digest realm="%s",'
                        'qop="auth",'
                        'algorithm="MD5",'
                        'nonce="%s"' % (realm, nonce))
    handler.end_headers()
    handler.rfile.read()
    handler.rfile.close()
    handler.wfile.write(msg.encode('utf8'))
    handler.wfile.close()

def _require_authenticate(func):
    '''A decorator to add digest authorization checks to HTTP Request Handlers'''

    def wrapped(self):
        if not hasattr(self, 'authenticated'):
            self.authenticated = None
        if self.authenticated:
            return func(self)

        auth = self.headers.get(u'Authorization')
        if auth is None:
            msg = u"You are not allowed to access this page. Please login first!"
            return _error_401(self, msg)

        token, fields = auth.split(' ', 1)
        if token != 'Digest':
            return _error_401(self, 'Unsupported authentication type')

        # Check the header fields of the request.
        cred = parse_http_list(fields)
        cred = parse_keqv_list(cred)
        keys = u'realm', u'username', u'nonce', u'uri', u'response'
        if not all(cred.get(key) for key in keys):
            return _error_401(self, 'Incomplete authentication header')
        if cred['realm'] != self.server.realm:
            return _error_401(self, 'Incorrect realm')
        if 'qop' in cred and ('nc' not in cred or 'cnonce' not in cred):
            return _error_401(self, 'qop with missing nc or cnonce')

        # Check the username.
        username = cred['username']
        password = self.server.get_password(username)
        if not username or password is None:
            return _error_401(self, 'Invalid username or password')

        # Check the digest string.
        location = u'%s:%s' % (self.command, self.path)
        location = md5hex(location.encode('utf8'))
        pwhash   = md5hex('%s:%s:%s' % (username, self.server.realm, password))

        if 'qop' in cred:
            info = (cred['nonce'],
                    cred['nc'],
                    cred['cnonce'],
                    cred['qop'],
                    location)
        else:
            info = cred['nonce'], location

        expect = u'%s:%s' % (pwhash, ':'.join(info))
        expect = md5hex(expect.encode('utf8'))
        if expect != cred['response']:
            return _error_401(self, 'Invalid username or password')

        # Success!
        self.authenticated = True
        return func(self)

    return wrapped


class HTTPServer(ThreadingMixIn, PyHTTPServer):
    daemon_threads = True

    def __init__(self, addr, rqh, user_data):
        self.debug           = False
        self.realm           = default_realm
        self.default_handler = None
        self.accounts        = {}
        self.handler_table   = {}
        self.user_data       = user_data
        PyHTTPServer.__init__(self, addr, rqh)

    def add_account(self, user, password):
        self.accounts[user] = password

    def get_password(self, username):
        return self.accounts.get(username)

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

    def _dbg(self, msg):
        if self.debug:
            print(msg)

    def get_handler(self, path):
        """returns none if no handler registered"""
        self._dbg("entering get_handler")
        if path in self.handler_table:
            self._dbg("path %s in self.handler_table."%path)
            self._dbg("self.handler_table[path] = %s" % self.handler_table[path])
            return self.handler_table[path]
        else:
            self._dbg("path %s NOT in self.handler_table."%path)
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

    def do_POSTGET(self, handler):
        """handle an HTTP request"""
        # at first, assume that the given path is the actual path and there are no arguments
        self.server._dbg(self.path)

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
        self.server._dbg(u"Preparing to call get_handler in do_POST")
        try:
            handler()
        except:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(format_exc().encode('utf8'))

    @_require_authenticate
    def do_POST(self):
        self.do_POSTGET(self.handle_POST)

    @_require_authenticate
    def do_GET(self):
        self.do_POSTGET(self.handle_GET)

    def handle_POST(self):
        self.send_response(404)
        self.end_headers()
        self.wfile.write('not found'.encode('utf8'))

    def handle_GET(self):
        self.send_response(404)
        self.end_headers()
        self.wfile.write('not found'.encode('utf8'))

    def send_response(self, code):
        BaseHTTPRequestHandler.send_response(self, code)
        self.send_header("Connection", "close")

if __name__ == '__main__':
    try:
        server = HTTPServer(('', 8123), HTTPRequestHandler)
        server.add_account('test', 'fo')
        print 'started httpserver...'
        server.serve_forever()
    except KeyboardInterrupt:
        print '^C received, shutting down server'
        server.socket.close()
