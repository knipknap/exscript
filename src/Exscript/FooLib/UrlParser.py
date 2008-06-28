#!/usr/bin/env python
# -*- coding: Latin-1 -*-
import re
from urlparse import urlparse, urlsplit

_hextochr = dict()
for i in range(256):
   _hextochr['%02x' % i] = chr(i)
   _hextochr['%02X' % i] = chr(i)

class Url(object):
    proto    = None
    user     = None
    password = None
    hostname = None
    port     = None
    path     = None
    vars     = None

def parse_url(url, default_protocol = 'telnet'):
    # We substitute the protocol name by 'http' to support the usual http URL
    # scheme, because Python's urlparse does not support our protocols
    # directly.
    protocol   = urlparse(url, default_protocol, 0)[0]
    url        = 'http://' + re.sub('^' + protocol + ':(?://)?', '', url)
    components = urlsplit(url, 'http', 0)
    netloc     = components[1]
    path       = components[2]
    query      = components[3]
    auth       = ''
    username   = None
    password   = None
    hostname   = netloc
    if netloc.find('@') >= 0:
        auth, hostname = netloc.split('@')

    # Parse username and password.
    if auth != '':
        username = auth
    auth = auth.split(':')
    if len(auth) == 1:
        username == auth[0]
    elif len(auth) == 2:
        username, password = auth

    # Build the result.
    result = Url()
    result.protocol = protocol
    result.username = username
    result.password = password
    result.hostname = hostname or path
    result.vars     = urlparse_qs('http://dummy/?' + query)
    return result


def unquote(s):
    """unquote('abc%20def') -> 'abc def'."""
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


def urlparse_qs(url, keep_blank_values=0, strict_parsing=0):
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
            name = unquote(nv[0].replace('+', ' '))
            value = unquote(nv[1].replace('+', ' '))
            query.append((name, value))

    dict = {}
    for name, value in query:
        if name in dict:
            dict[name].append(value)
        else:
            dict[name] = [value]
    return dict


if __name__ == '__main__':
    import unittest
    
    class ParseUrlTest(unittest.TestCase):
        def runTest(self):
            urls = ['testhost',
                    'testhost?myvar=testvalue',
                    'user@testhost',
                    'user@testhost?myvar=testvalue',
                    'user:mypass@testhost',
                    'user:mypass@testhost?myvar=testvalue',
                    'ssh:testhost',
                    'ssh:testhost?myvar=testvalue',
                    'ssh://testhost',
                    'ssh://testhost?myvar=testvalue',
                    'ssh://user@testhost',
                    'ssh://user@testhost?myvar=testvalue',
                    'ssh://user:password@testhost',
                    'ssh://user:password@testhost?myvar=testvalue',
                    'ssh://user:password@testhost',
                    'ssh://user:password@testhost?myvar=testvalue&myvar2=test%202',
                    'ssh://user:password@testhost?myvar=testvalue&amp;myvar2=test%202']
            for url in urls:
                print '%s:\n%s' % (url, parse_url(url))

    test = ParseUrlTest()
    test.runTest()
