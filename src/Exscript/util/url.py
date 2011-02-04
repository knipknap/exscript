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
Working with URLs (as used in URL formatted hostnames).
"""
import re
from urllib      import urlencode, quote
from urlparse    import urlparse, urlsplit
from collections import defaultdict

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
def _unquote(string):
    """_unquote('abc%20def') -> 'abc def'."""
    result = string.split('%')
    for i, item in enumerate(result[1:]):
        i += 1
        try:
            result[i] = _hextochr[item[:2]] + item[2:]
        except KeyError:
            result[i] = '%' + item
        except UnicodeDecodeError:
            result[i] = unichr(int(item[:2], 16)) + item[2:]
    return ''.join(result)

def _urlparse_qs(url, keep_blank_values=0, strict_parsing=0):
    """
    Parse a URL query string and return the components as a dictionary.

    Based on the cgi.parse_qs method.This is a utility function provided
    with urlparse so that users need not use cgi module for
    parsing the url query string.

    Arguments:

      - url: URL with query string to be parsed

      - keep_blank_values: flag indicating whether blank values in
        URL encoded queries should be treated as blank strings.
        A true value indicates that blanks should be retained as
        blank strings.  The default false value indicates that
        blank values are to be ignored and treated as if they were
        not included.

      - strict_parsing: flag indicating what to do with parsing errors.
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
    protocol  = None
    username  = None
    password1 = None
    password2 = None
    hostname  = None
    port      = None
    path      = None
    vars      = None

    def __str__(self):
        url = ''
        if self.protocol is not None:
            url += self.protocol + '://'
        if self.username is not None or \
           self.password1 is not None or \
           self.password2 is not None:
            if self.username is not None:
                url += quote(self.username, '')
            if self.password1 is not None or self.password2 is not None:
                url += ':'
            if self.password1 is not None:
                url += quote(self.password1, '')
            if self.password2 is not None:
                url += ':' + quote(self.password2, '')
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
            url += '?' + urlencode(pairs)
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
    if url is None:
        raise TypeError('Expected string but got' + type(url))

    # Extract the protocol name from the URL.
    result = Url()
    match  = re.match(r'(\w+)://', url)
    if match:
        result.protocol = match.group(1)
    else:
        result.protocol = default_protocol

    # Now remove the query from the url.
    query = ''
    if '?' in url:
        url, query = url.split('?', 1)
    result.vars = _urlparse_qs('http://dummy/?' + query)

    # Substitute the protocol name by 'http', because Python's urlsplit
    # fails on our protocol names otherwise.
    prefix = result.protocol + '://'
    if url.startswith(prefix):
        url = url[len(prefix):]
    url = 'http://' + url

    # Parse the remaining url.
    parsed = urlsplit(url, 'http', False)
    netloc = parsed[1]

    # Parse username and password.
    auth = ''
    if '@' in netloc:
        auth, netloc = netloc.split('@')
        auth = auth.split(':')
        try:
            result.username  = _unquote(auth[0])
            result.password1 = _unquote(auth[1])
            result.password2 = _unquote(auth[2])
        except IndexError:
            pass

    # Parse hostname and port number.
    result.hostname = netloc + parsed.path
    result.port     = _well_known_ports.get(result.protocol)
    if ':' in netloc:
        result.hostname, port = netloc.split(':')
        result.port           = int(port)

    return result
