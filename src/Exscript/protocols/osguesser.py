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
OS guesser for any protocol to auto-select a device driver.
"""

import logging

from .drivers import drivers

_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())


class OsGuesser:
    """
    The OsGuesser monitors everything that happens on a Protocol, and attempts to
    collect data out of the network activity. It watches for specific patterns in the
    network traffic to decide what operating system a connected host is running. It is
    completely passive, and attempts no changes on the protocol adapter. However, the
    protocol adapter may request information from the OsGuesser, and perform changes
    based on the information provided.
    """

    def __init__(self):
        self._logger = _logger
        self._buffer_limit = 512
        self._auth_os_map = [d._check_head for d in drivers]
        self._netconf_os_map = [d._check_netconf for d in drivers]
        self._protocol_os_map = [d._check_protocol for d in drivers]
        self._response_os_map = [d._check_response for d in drivers]
        self.debug = 0
        self._init()

    def _init(self):
        self._auth_buffer = ''
        self._protocol_buffer = ''
        self._response_buffer = ''
        self._info = {"os": ("unknown", 0)}

    def _dbg(self, level, msg, exc_info=None):
        if level > self.debug:
            return
        self._logger.debug(msg, exc_info=exc_info)

    def reset(self, auth_buffer='', protocol_buffer='', response_buffer=''):
        """
        Reset the guesser state and optionally pre-populate the monitoring buffers.
        """
        msg = "Reset with new buffers: auth=%r, protocol=%r, response=%r"
        self._dbg(2, msg % (auth_buffer, protocol_buffer, response_buffer))
        self._init()
        self._auth_buffer = auth_buffer
        self._protocol_buffer = protocol_buffer
        self._response_buffer = response_buffer

    def set(self, key, value, confidence=100):
        """
        Defines the given value with the given confidence, unless the same
        value is already defined with a higher confidence level.
        """
        if value is None:
            return
        old_value, old_confidence = self._info.get(key, (None, None))
        if old_confidence is not None and old_confidence >= confidence:
            return
        self._dbg(
            2,
            "Higher confidence for %s: %s with %s -> %s with %s"
            % (key, old_value, old_confidence, value, confidence),
        )
        self._info[key] = (value, confidence)

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
        if key not in self._info:
            return None
        value, conf = self._info.get(key)
        if conf >= confidence:
            return value
        return None

    def check_received_data(self, data, authenticated):
        """
        Callback to search the received data for matching patterns.

        The `authenticated` flag controls whether to also evaluate received data
        from the authentication phase.
        """
        if not data:
            return
        if authenticated:
            self._response_buffer += data
            # Stop looking if we are already 80 percent certain.
            if self.get('os', 80) in ('unknown', None):
                self._dbg(3, "Matching received data: %r" % self._response_buffer)
                self.set_from_match('os', self._response_os_map, self._response_buffer)
            self._response_buffer = self._response_buffer[-self._buffer_limit :]
            return

        self._auth_buffer += data
        self._dbg(3, "Matching authentication buffer: %r" % self._auth_buffer)
        self.set_from_match('os', self._auth_os_map, self._auth_buffer)
        self.set_from_match('os', self._response_os_map, self._auth_buffer)
        self._auth_buffer = self._auth_buffer[-self._buffer_limit :]

    def check_protocol_info(self, data):
        """
        Callback to search the received protocol information for matching patterns.
        """
        if not data:
            return
        self._protocol_buffer += data
        self._dbg(3, "Matching protocol info: %r" % self._protocol_buffer)
        self.set_from_match('os', self._protocol_os_map, self._protocol_buffer)
        self._protocol_buffer = self._protocol_buffer[-self._buffer_limit :]

    def check_netconf_capabilities(self, capabilities):
        """
        Callback to search the received Netconf capabilities for matching patterns.
        """
        if not capabilities:
            return
        if not isinstance(capabilities, str):
            capabilities = "\n".join(capabilities)
        self._dbg(3, "Matching Netconf capabilities: %r" % capabilities)
        self.set_from_match('os', self._netconf_os_map, capabilities)
