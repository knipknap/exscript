#
# Copyright (C) 2001-2023 Python Software Foundation; All Rights Reserved
# Copyright (C) 2010-2017 Samuel Abels
#
# SPDX-License-Identifier: PSF-2.0 AND MIT
#
# This module is derived from the telnetlib module of CPython 3.12, which is
# licensed under the Python Software Foundation License Version 2; see
# LICENSES/PSF-2.0.txt. The changes for Exscript are licensed under the MIT
# License; see COPYING.
#
# Summary of the changes made to Python's telnetlib, as required by the PSF
# License: received data is decoded with a configurable encoding and passed to
# a callback, and NUL bytes are removed from it (the original also removed
# XON); the terminal type (TTYPE) and window size (NAWS) options are
# negotiated and the echo option is accepted, all other options are refused;
# commands are parsed in whole reads instead of byte by byte; the client waits
# for any of several regular expressions in a search window that a cleanup
# function can process; the read_*() variants, interact(), the option
# negotiation callback and the deprecation warning were removed.
"""
The Telnet client (RFC 854) of Exscript's Telnet adapter, derived from the
telnetlib module of CPython.

This module is internal; use :class:`Exscript.protocols.Telnet` instead.
"""

import codecs
import logging
import re
import select
import socket
import struct
from io import StringIO
from time import monotonic

__all__ = ['Telnet']

_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())

TELNET_PORT = 23

# Telnet commands (RFC 854) and the options that Exscript negotiates.
IAC = 255  # interpret as command
DONT = 254
DO = 253
WONT = 252
WILL = 251
SB = 250  # subnegotiation begin
SE = 240  # subnegotiation end
ECHO = 1
TTYPE = 24  # terminal type (RFC 1091)
NAWS = 31  # window size (RFC 1073)
TTYPE_IS = 0
TTYPE_SEND = 1

_NEGOTIATION = {DO: 'DO', DONT: 'DONT', WILL: 'WILL', WONT: 'WONT'}
_IAC = bytes([IAC])

# _waitfor() searches the end of the received text after every read, so its
# search window covers all data only with small reads.
_READ_SIZE = 64


def _command(*codes):
    return bytes([IAC, *codes])


class Telnet:
    """
    A Telnet connection that answers option negotiation and delivers the
    received text to a callback and to expect().
    """

    def __init__(
        self,
        host=None,
        port=0,
        encoding='latin-1',
        *,
        connect_timeout=None,
        termsize=None,
        termtype='dumb',
        receive_callback=None,
    ):
        """
        Constructor. Connects to the host if one is given.

        :type  host: str|None
        :param host: The host name or address.
        :type  port: int
        :param port: The TCP port; 0 is the Telnet port 23.
        :type  encoding: str
        :param encoding: The encoding of the sent and received text.
        :type  connect_timeout: float|None
        :param connect_timeout: The timeout of socket operations in seconds.
        :type  termsize: tuple(int, int)|None
        :param termsize: The rows and columns of the terminal (NAWS).
        :type  termtype: str
        :param termtype: The terminal type (TTYPE).
        :type  receive_callback: callable|None
        :param receive_callback: Called with every received text.
        """
        self.debuglevel = 0
        self.host = host
        self.port = port
        self.sock = None
        self.encoding = encoding
        self.connect_timeout = connect_timeout
        self.window_size = termsize
        self.termtype = termtype
        self.data_callback = receive_callback
        self.cancel_expect = False
        self.can_naws = False
        self.eof = False
        self.rawq = b''  # received bytes that end with an incomplete command
        self.cookedq = StringIO()
        self._decoder = codecs.getincrementaldecoder(encoding)()
        self._sb = None  # the data of the subnegotiation in progress
        if host:
            self.open(host, port)

    def open(self, host, port=0):
        """
        Connects to the host, trying all of its addresses (IPv4 and IPv6).

        :type  host: str
        :param host: The host name or address.
        :type  port: int
        :param port: The TCP port; 0 is the Telnet port 23.
        """
        self.eof = False
        self.host = host
        self.port = port or TELNET_PORT
        try:
            self.sock = socket.create_connection((host, self.port), self.connect_timeout)
        except OSError as exc:
            raise OSError(f'{exc} => telnet://{host}:{self.port}') from exc

    def msg(self, msg, *args):
        """Logs a debug message if the debug level is above 0."""
        if self.debuglevel > 0:
            _logger.debug(msg, *args)

    def set_debuglevel(self, debuglevel):
        """
        Sets the debug level; above 0, the received data and the option
        negotiation are logged.

        :type  debuglevel: int
        :param debuglevel: The debug level.
        """
        self.debuglevel = debuglevel

    def close(self):
        """Closes the connection."""
        sock, self.sock = self.sock, None
        self.eof = True
        if sock:
            sock.close()

    def write(self, buffer):
        """
        Sends the given text or bytes, doubling the IAC bytes. The data is not
        logged, because it may contain a password.

        :type  buffer: str|bytes
        :param buffer: The data to send.
        """
        if isinstance(buffer, str):
            buffer = buffer.encode(self.encoding)
        self.sock.sendall(buffer.replace(_IAC, _IAC + _IAC))

    def set_window_size(self, rows, cols):
        """
        Sets the window size, and sends it if the server asked for it (NAWS).

        :type  rows: int
        :param rows: The number of rows.
        :type  cols: int
        :param cols: The number of columns.
        """
        self.window_size = rows, cols
        if not self.can_naws:
            return
        size = struct.pack('!HH', min(cols, 0xFFFF), min(rows, 0xFFFF))
        self.sock.sendall(_command(SB, NAWS) + size.replace(_IAC, _IAC + _IAC) + _command(SE))

    def _negotiate(self, command, option):
        self.msg('IAC %s %d', _NEGOTIATION[command], option)
        if command == DO and option in (TTYPE, NAWS):
            self.sock.sendall(_command(WILL, option))
            if option == NAWS:
                self.can_naws = True
                if self.window_size:
                    self.set_window_size(*self.window_size)
        elif command in (DO, DONT):
            self.sock.sendall(_command(WONT, option))
        elif option == ECHO:
            # Exscript always asks for the echo, also when the server refuses it.
            self.sock.sendall(_command(DO, option))
        else:
            self.sock.sendall(_command(DONT, option))

    def _subnegotiate(self, data):
        self.msg('IAC SB %r', data)
        if data == bytes([TTYPE, TTYPE_SEND]):
            self.msg('Indicating support for terminal type %s.', self.termtype)
            ttype = self.termtype.encode('latin-1')
            self.sock.sendall(_command(SB, TTYPE, TTYPE_IS) + ttype + _command(SE))

    def process_rawq(self):
        """
        Moves the received data from the raw queue to the cooked queue,
        removes the Telnet commands and answers the option negotiation.
        Keeps an incomplete command in the raw queue until more data arrives,
        so it never blocks.
        """
        data, self.rawq = self.rawq, b''
        cooked = bytearray()
        pos, end = 0, len(data)
        while pos < end:
            iac = data.find(IAC, pos)
            if self._sb is not None:  # inside a subnegotiation
                if iac < 0:
                    self._sb += data[pos:]
                    break
                self._sb += data[pos:iac]
                if iac + 1 == end:
                    self.rawq = data[iac:]
                    break
                code = data[iac + 1]
                if code == IAC:
                    self._sb.append(IAC)
                    pos = iac + 2
                    continue
                sb, self._sb = bytes(self._sb), None
                if code == SE:
                    self._subnegotiate(sb)
                    pos = iac + 2
                else:
                    pos = iac  # the subnegotiation is not terminated: handle the command
                continue
            if iac < 0:
                cooked += data[pos:]
                break
            cooked += data[pos:iac]
            if iac + 1 == end or (iac + 2 == end and data[iac + 1] in _NEGOTIATION):
                self.rawq = data[iac:]
                break
            code = data[iac + 1]
            pos = iac + 2
            if code == IAC:
                cooked.append(IAC)
            elif code in _NEGOTIATION:
                self._negotiate(code, data[pos])
                pos += 1
            elif code == SB:
                self._sb = bytearray()
            else:
                self.msg('IAC %d ignored', code)  # e.g. NOP or go ahead
        if self.eof:  # an incomplete command can no longer complete
            self.rawq = b''
            self._sb = None
        text = self._decoder.decode(bytes(cooked).replace(b'\0', b''), self.eof)
        if text:
            self.cookedq.write(text)
            if self.data_callback is not None:
                self.data_callback(text)

    def fill_rawq(self):
        """
        Reads once from the socket into the raw queue. Blocks if no data is
        available, and sets eof when the connection was closed.
        """
        data = self.sock.recv(_READ_SIZE)
        self.msg('Recv: %r', data)
        self.eof = not data
        self.rawq += data

    def _read_cooked(self):
        text = self.cookedq.getvalue()
        self.cookedq.seek(0)
        self.cookedq.truncate()
        return text

    def read_all(self):
        """
        Reads until the connection is closed.

        :rtype:  str
        :return: The received text that expect() did not consume.
        """
        self.process_rawq()
        while not self.eof:
            self.fill_rawq()
            self.process_rawq()
        return self._read_cooked()

    def _wait_for_data(self, timeout):
        # Waits in steps of one second; a single select() with the full timeout
        # did not always return when data arrived.
        end = monotonic() + timeout
        while True:
            readable, _, _ = select.select([self.sock], [], [], 1)
            if readable:
                return True
            if monotonic() > end:
                return False

    def _waitfor(self, relist, timeout=None, flush=False, cleanup=None):
        relist = [regex if hasattr(regex, 'search') else re.compile(regex) for regex in relist]
        search_window_size = 150
        head_lookback_size = 10
        self.msg('Expecting: %s', [regex.pattern for regex in relist])
        incomplete_tail = ''
        clean_sw_size = search_window_size
        while True:
            self.process_rawq()
            if self.cancel_expect:
                self.cancel_expect = False
                self.msg('Cancelling expect()')
                return -2, None, ''
            qlen = self.cookedq.tell()
            if cleanup:
                while True:
                    pos = qlen - clean_sw_size - len(incomplete_tail) - head_lookback_size
                    self.cookedq.seek(max(0, pos))
                    search_window = self.cookedq.read()
                    search_window, incomplete_tail = cleanup(search_window)
                    search_window_len = len(search_window)
                    if clean_sw_size > qlen or search_window_len >= search_window_size:
                        search_window = search_window[-search_window_size:]
                        if search_window_len > search_window_size:
                            clean_sw_size -= search_window_size
                        break
                    clean_sw_size += search_window_size
            else:
                self.cookedq.seek(max(0, qlen - search_window_size))
                search_window = self.cookedq.read()
            for index, regex in enumerate(relist):
                match = regex.search(search_window)
                if match is None:
                    continue
                self.msg('Match found: %r', match.group())
                self.cookedq.seek(0)
                text = self.cookedq.read(qlen - (match.end() - match.start()))
                if flush:
                    self.cookedq.seek(0)
                    self.cookedq.truncate()
                    self.cookedq.write(search_window[match.end() :])
                else:
                    self.cookedq.seek(qlen)
                return index, match, text
            if self.eof:
                break
            if timeout is not None and not self._wait_for_data(timeout):
                break
            self.fill_rawq()
        text = self._read_cooked()
        if not text and self.eof:
            raise EOFError('telnet connection closed')
        return -1, None, text

    def waitfor(self, relist, timeout=None, cleanup=None):
        """
        Reads until one of the regular expressions matches the end of the
        received text, and keeps the text.

        Returns a tuple of the index of the first regular expression that
        matched, the match object, and the text up to the match. When nothing
        matched until the timeout, returns (-1, None, text) with the received
        text; when expect was cancelled, returns (-2, None, ''). Raises
        EOFError if the connection was closed and no text was received.

        :type  relist: list(str|re.Pattern)
        :param relist: The regular expressions.
        :type  timeout: float|None
        :param timeout: Seconds without received data until the timeout.
        :type  cleanup: callable|None
        :param cleanup: Returns the text to search and an incomplete tail.
        :rtype:  tuple(int, re.Match|None, str)
        :return: The index, the match, and the text.
        """
        return self._waitfor(relist, timeout, flush=False, cleanup=cleanup)

    def expect(self, relist, timeout=None, cleanup=None):
        """
        Like waitfor(), but removes the text up to the end of the match.

        :type  relist: list(str|re.Pattern)
        :param relist: The regular expressions.
        :type  timeout: float|None
        :param timeout: Seconds without received data until the timeout.
        :type  cleanup: callable|None
        :param cleanup: Returns the text to search and an incomplete tail.
        :rtype:  tuple(int, re.Match|None, str)
        :return: The index, the match, and the text.
        """
        return self._waitfor(relist, timeout, flush=True, cleanup=cleanup)
