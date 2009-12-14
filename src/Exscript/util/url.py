# Copyright (C) 2007-2009 Samuel Abels.
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
import re, urllib
from urlparse import urlparse, urlsplit

_hextochr = dict()
for i in range(256):
    _hextochr['%02x' % i] = chr(i)
    _hextochr['%02X' % i] = chr(i)

_well_known_ports = {
    'ftp':    21,
    'ssh':    22,
    'ssh1':   22,
    'ssh2':   22,
    'telnet': 23,
    'smtp':   25,
    'http':   80,
    'pop3':  110,
    'imap':  143
}

###############################################################
# utils
###############################################################
def _unquote(s):
    """_unquote('abc%20def') -> 'abc def'."""
    res = s.split('%')
    for i in xrange(1, len(res)):
        item = res[i]
        try:
            res[i] = _hextochr[item[:2]] + item[2:]
        except KeyError:
            res[i] = '%' + item
        except UnicodeDecodeError:
            res[i] = unichr(int(item[:2], 16)) + item[2:]
    return "".join(res)

def _urlparse_qs(url, keep_blank_values=0, strict_parsing=0):
    """Parse a URL query string and return the components as a dictionary.

    Based on the cgi.parse_qs method.This is a utility function provided
    with urlparse so that users need not use cgi module for
    parsing the url query string.

        Arguments:

        url: URL with query string to be parsed

        keep_blank_values: flag indicating whether blank values in
            URL encoded queries should be treated as blank strings.
            A true value indicates that blanks should be retained as
            blank strings.  The default false value indicates that
            blank values are to be ignored and treated as if they were
            not included.

        strict_parsing: flag indicating what to do with parsing errors.
            If false (the default), errors are silently ignored.
            If true, errors raise a ValueError exception.
    """

    scheme, netloc, url, params, querystring, fragment = urlparse(url)

    pairs = [s2 for s1 in querystring.split('&') for s2 in s1.split(';')]
    query = []
    for name_value in pairs:
        if not name_value and not strict_parsing:
            continue
        nv = name_value.split('=', 1)
        if len(nv) != 2:
            if strict_parsing:
                raise ValueError, "bad query field: %r" % (name_value,)
            # Handle case of a control-name with no equal sign
            if keep_blank_values:
                nv.append('')
            else:
                continue
        if len(nv[1]) or keep_blank_values:
            name = _unquote(nv[0].replace('+', ' '))
            value = _unquote(nv[1].replace('+', ' '))
            query.append((name, value))

    dict = {}
    for name, value in query:
        if name in dict:
            dict[name].append(value)
        else:
            dict[name] = [value]
    return dict

###############################################################
# public api
###############################################################
class Url(object):
    """
    Represents a URL.
    """
    protocol = None
    username = None
    password = None
    hostname = None
    port     = None
    path     = None
    vars     = None

    def __str__(self):
        url = ''
        if self.protocol:
            url += self.protocol + '://'
        if self.username is not None:
            url += self.username
            if self.password:
                url += ':' + self.password
            url += '@'
        url += self.hostname
        if self.port:
            url += ':' + str(self.port)
        if self.path:
            url += '/' + self.path

        if self.vars:
            pairs = []
            for key, values in self.vars.iteritems():
                for value in values:
                    pairs.append((key, value))
            url += '?' + urllib.urlencode(pairs)
        return url

def parse_url(url, default_protocol = 'telnet'):
    """
    Parses the given URL and returns an URL object. There are some differences
    to Python's built-in URL parser:

      - It is less strict, many more inputs are accepted. This is necessary to
      allow for passing a simple hostname as a URL.
      - You may specify a default protocol that is used when the http://
      portion is missing.
      - The port number defaults to the well-known port of the given protocol.
      - The query variables are parsed into a dictionary (Url.vars).

    @type  url: string
    @param url: A URL.
    @type  default_protocol: string
    @param default_protocol: A protocol name.
    @rtype:  Url
    @return: The Url object contructed from the given URL.
    """
    # We substitute the protocol name by 'http' to support the usual http URL
    # scheme, because Python's urlparse does not support our protocols
    # directly.
    # In Python < 2.4, urlsplit can not handle query variables, so we split
    # them away.
    result          = Url()
    result.protocol = urlparse(url, default_protocol, 0)[0]
    result.port     = _well_known_ports.get(result.protocol)
    uri             = 'http://' + re.sub('^' + result.protocol + ':(?://)?', '', url)
    location        = uri
    query           = ''
    if '?' in uri:
        location, query = uri.split('?', 1)
    components      = urlsplit(location, 'http', 0)
    netloc          = components[1]
    path            = components[2]
    auth            = ''
    if netloc.find('@') >= 0:
        auth, netloc = netloc.split('@')

    # Parse the hostname/port number.
    netloc   = netloc.split(':')
    hostname = netloc[0]
    if len(netloc) == 2:
        result.port = int(netloc[1])

    # Parse username and password.
    if auth != '':
        result.username = auth
    auth = auth.split(':')
    if len(auth) == 1:
        result.username == auth[0]
    elif len(auth) == 2:
        result.username, result.password = auth

    # Build the result.
    if not hostname and '/' in path:
        result.hostname = None
    elif not hostname:
        result.hostname = path
    else:
        result.hostname = hostname
    result.path = path
    result.vars = _urlparse_qs('http://dummy/?' + query)
    return result
