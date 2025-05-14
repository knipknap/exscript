#
# Copyright (C) 2010-2017 Samuel Abels
# The MIT License (MIT)
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Working with URLs (as used in URL formatted hostnames).
"""
from __future__ import unicode_literals, absolute_import
from builtins import str
from builtins import chr
from builtins import range
from builtins import object
import re
from urllib.parse import urlencode, quote
from urllib.parse import urlparse, urlsplit
from .collections import OrderedDefaultDict

def _make_hexmap():
    hexmap = dict()
    for i in range(256):
        hexmap['%02x' % i] = chr(i)
        hexmap['%02X' % i] = chr(i)
    return hexmap

_HEXTOCHR = _make_hexmap()

_WELL_KNOWN_PORTS = {
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

def _unquote(string):
    """_unquote('abc%20def') -> 'abc def'."""
    result = string.split('%')
    for i, item in enumerate(result[1:]):
        i += 1
        try:
            result[i] = _HEXTOCHR[item[:2]] + item[2:]
        except KeyError:
            result[i] = '%' + item
        except UnicodeDecodeError:
            result[i] = chr(int(item[:2], 16)) + item[2:]
    return ''.join(result)

def _urlparse_qs(url):
    """
    Parse a URL query string and return the components as a dictionary.

    Based on the cgi.parse_qs method.This is a utility function provided
    with urlparse so that users need not use cgi module for
    parsing the url query string.

    Arguments:

    :type url: str
    :param url: URL with query string to be parsed
    """
    # Extract the query part from the URL.
    querystring = urlparse(url)[4]

    # Split the query into name/value pairs.
    pairs = [s2 for s1 in querystring.split('&') for s2 in s1.split(';')]

    # Split the name/value pairs.
    result = OrderedDefaultDict(list)
    for name_value in pairs:
        pair = name_value.split('=', 1)
        if len(pair) != 2:
            continue

        if len(pair[1]) > 0:
            name = _unquote(pair[0].replace('+', ' '))
            value = _unquote(pair[1].replace('+', ' '))
            result[name].append(value)

    return result

class Url(object):

    """
    Represents a URL.
    """

    def __init__(self):
        self.protocol = None
        self.username = None
        self.password1 = None
        self.password2 = None
        self.hostname = None
        self.port = None
        self.path = None
        self.vars = None

    def __str__(self):
        """
        Like :class:`to_string()`.

        :rtype:  str
        :return: A URL.
        """
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
            for key, values in self.vars.items():
                for value in values:
                    pairs.append((key, value))
            url += '?' + urlencode(pairs)
        return url

    def to_string(self):
        """
        Returns the URL, including all attributes, as a string.

        :rtype:  str
        :return: A URL.
        """
        return str(self)

    @staticmethod
    def from_string(url, default_protocol='telnet'):
        """
        Parses the given URL and returns an URL object. There are some
        differences to Python's built-in URL parser:

        - It is less strict, many more inputs are accepted. This is
          necessary to allow for passing a simple hostname as a URL.
        - You may specify a default protocol that is used when the http://
          portion is missing.
        - The port number defaults to the well-known port of the given
          protocol.
        - The query variables are parsed into a dictionary (Url.vars).

        :type  url: str
        :param url: A URL.
        :type  default_protocol: string
        :param default_protocol: A protocol name.
        :rtype:  Url
        :return: The Url object constructed from the given URL.
        """
        if url is None:
            raise TypeError('Expected string but got' + type(url))

        # Extract the protocol name from the URL.
        result = Url()
        match = re.match(r'(\w+)://', url)
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
                result.username = _unquote(auth[0])
                result.password1 = _unquote(auth[1])
                result.password2 = _unquote(auth[2])
            except IndexError:
                pass

        # Parse hostname and port number.
        result.hostname = netloc + parsed.path
        result.port = _WELL_KNOWN_PORTS.get(result.protocol)
        if ':' in netloc:
            result.hostname, port = netloc.split(':')
            result.port = int(port)

        return result
