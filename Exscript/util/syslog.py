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
Send messages to a syslog server.
"""
import os
import sys
import imp
import socket

# This way of loading a module prevents Python from looking in the
# current directory. (We need to avoid it due to the syslog module
# name collision.)
syslog = imp.load_module('syslog', *imp.find_module('syslog'))


def netlog(message,
           source=None,
           host='localhost',
           port=514,
           priority=syslog.LOG_DEBUG,
           facility=syslog.LOG_USER):
    """
    Python's built in syslog module does not support networking, so
    this is the alternative.
    The source argument specifies the message source that is
    documented on the receiving server. It defaults to "scriptname[pid]",
    where "scriptname" is sys.argv[0], and pid is the current process id.
    The priority and facility arguments are equivalent to those of
    Python's built in syslog module.

    :type  source: str
    :param source: The source address.
    :type  host: str
    :param host: The IP address or hostname of the receiving server.
    :type  port: str
    :param port: The TCP port number of the receiving server.
    :type  priority: int
    :param priority: The message priority.
    :type  facility: int
    :param facility: The message facility.
    """
    if not source:
        source = '%s[%s]' + (sys.argv[0], os.getpid())
    data = '<%d>%s: %s' % (priority + facility, source, message)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(data, (host, port))
    sock.close()
