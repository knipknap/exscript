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
from __future__ import print_function
from builtins import object
from Exscript.protocols.drivers import drivers


class OsGuesser(object):

    """
    The OsGuesser monitors everything that happens on a Protocol,
    and attempts to collect data out of the network activity.
    It watches for specific patterns in the network traffic to decide
    what operating system a connected host is running.
    It is completely passive, and attempts no changes on the protocol
    adapter. However, the protocol adapter may request information
    from the OsGuesser, and perform changes based on the information
    provided.
    """

    def __init__(self):
        self.info = {}
        self.debug = False
        self.protocol_os_map = [d._check_protocol for d in drivers]
        self.auth_os_map = [d._check_head for d in drivers]
        self.os_map = [d._check_response for d in drivers]
        self.auth_buffer = ''
        self.set('os', 'unknown', 0)

    def reset(self, auth_buffer=''):
        self.__init__()
        self.auth_buffer = auth_buffer

    def set(self, key, value, confidence=100):
        """
        Defines the given value with the given confidence, unless the same
        value is already defined with a higher confidence level.
        """
        if value is None:
            return
        if key in self.info:
            old_confidence, old_value = self.info.get(key)
            if old_confidence >= confidence:
                return
        self.info[key] = (confidence, value)

    def set_from_match(self, key, regex_list, string):
        """
        Given a list of functions or three-tuples (regex, value, confidence),
        this function walks through them and checks whether any of the
        items in the list matches the given string.
        If the list item is a function, it must have the following
        signature::

            func(string) : (string, int)

        Where the return value specifies the resulting value and the
        confidence of the match.
        If a match is found, and the confidence level is higher
        than the currently defined one, the given value is defined with
        the given confidence.
        """
        for item in regex_list:
            if hasattr(item, '__call__'):
                self.set(key, *item(string))
            else:
                regex, value, confidence = item
                if regex.search(string):
                    self.set(key, value, confidence)

    def get(self, key, confidence=0):
        """
        Returns the info with the given key, if it has at least the given
        confidence. Returns None otherwise.
        """
        if key not in self.info:
            return None
        conf, value = self.info.get(key)
        if conf >= confidence:
            return value
        return None

    def data_received(self, data, app_authentication_done):
        # If the authentication procedure is complete, use the normal
        # "runtime" matchers.
        if app_authentication_done:
            # Stop looking if we are already 80 percent certain.
            if self.get('os', 80) in ('unknown', None):
                self.set_from_match('os', self.os_map, data)
            return

        # Else, check the head that we collected so far.
        self.auth_buffer += data
        if self.debug:
            print("DEBUG: Matching buffer:", repr(self.auth_buffer))
        self.set_from_match('os', self.auth_os_map, self.auth_buffer)
        self.set_from_match('os', self.os_map,      self.auth_buffer)

    def protocol_info(self, data):
        if self.debug:
            print("DEBUG: Protocol info:", repr(data))
        self.set_from_match('os', self.protocol_os_map, data)
