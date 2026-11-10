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
# commands are parsed in whole reads instead of byte by byte; receive() waits
# for one read with a timeout; expect(), the read_*() variants, interact(),
# the option negotiation callback and the deprecation warning were removed.
"""
The Telnet client (RFC 854) of Exscript's Telnet adapter, derived from the
telnetlib module of CPython.

This module is internal; use :class:`Exscript.protocols.Telnet` instead.
"""

import codecs
import logging
import socket
import struct
from collections.abc import Callable
from typing import Any, cast

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

_READ_SIZE = 65536


def _command(*codes: int) -> bytes:
    """
    Returns a Telnet command: IAC followed by the given codes.
    """
    return bytes([IAC, *codes])


class Telnet:
    """
    A Telnet connection that answers the option negotiation and passes the
    received text to a callback.
    """

    def __init__(
        self,
        host: str | None = None,
        port: int = 0,
        encoding: str = 'latin-1',
        *,
        connect_timeout: float | None = None,
        termsize: tuple[int, int] | None = None,
        termtype: str = 'dumb',
        receive_callback: Callable[[str], object] | None = None,
    ) -> None:
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
        # Set by open(). The methods that send or receive need a connection;
        # they cast the socket for the type checker.
        self.sock: socket.socket | None = None
        self.encoding = encoding
        self.connect_timeout = connect_timeout
        self.window_size = termsize
        self.termtype = termtype
        self.data_callback = receive_callback
        self.can_naws = False
        self.eof = False
        self.rawq = b''  # received bytes that end with an incomplete command
        self._decoder = codecs.getincrementaldecoder(encoding)()
        self._sb: bytearray | None = None  # the data of the subnegotiation in progress
        if host:
            self.open(host, port)

    def open(self, host: str, port: int = 0) -> None:
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

    def msg(self, msg: str, *args: Any) -> None:
        """Logs a debug message if the debug level is above 0."""
        if self.debuglevel > 0:
            _logger.debug(msg, *args)

    def set_debuglevel(self, debuglevel: int) -> None:
        """
        Sets the debug level; above 0, the received data and the option
        negotiation are logged.

        :type  debuglevel: int
        :param debuglevel: The debug level.
        """
        self.debuglevel = debuglevel

    def close(self) -> None:
        """Closes the connection."""
        sock, self.sock = self.sock, None
        self.eof = True
        if sock:
            sock.close()

    def write(self, buffer: str | bytes) -> None:
        """
        Sends the given text or bytes, doubling the IAC bytes. The data is not
        logged, because it may contain a password.

        :type  buffer: str|bytes
        :param buffer: The data to send.
        """
        if isinstance(buffer, str):
            buffer = buffer.encode(self.encoding)
        cast(socket.socket, self.sock).sendall(buffer.replace(_IAC, _IAC + _IAC))

    def set_window_size(self, rows: int, cols: int) -> None:
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
        cast(socket.socket, self.sock).sendall(
            _command(SB, NAWS) + size.replace(_IAC, _IAC + _IAC) + _command(SE)
        )

    def _negotiate(self, command: int, option: int) -> None:
        """
        Answers an option negotiation command (DO, DONT, WILL or WONT) of the
        server: agrees to send the terminal type and the window size, asks
        for the echo, and refuses all other options.
        """
        self.msg('IAC %s %d', _NEGOTIATION[command], option)
        if command == DO and option in (TTYPE, NAWS):
            cast(socket.socket, self.sock).sendall(_command(WILL, option))
            if option == NAWS:
                self.can_naws = True
                if self.window_size:
                    self.set_window_size(*self.window_size)
        elif command in (DO, DONT):
            cast(socket.socket, self.sock).sendall(_command(WONT, option))
        elif option == ECHO:
            # Exscript always asks for the echo, also when the server refuses it.
            cast(socket.socket, self.sock).sendall(_command(DO, option))
        else:
            cast(socket.socket, self.sock).sendall(_command(DONT, option))

    def _subnegotiate(self, data: bytes) -> None:
        """
        Answers the given subnegotiation of the server: sends the terminal
        type if the server asks for it.
        """
        self.msg('IAC SB %r', data)
        if data == bytes([TTYPE, TTYPE_SEND]):
            self.msg('Indicating support for terminal type %s.', self.termtype)
            ttype = self.termtype.encode('latin-1')
            cast(socket.socket, self.sock).sendall(
                _command(SB, TTYPE, TTYPE_IS) + ttype + _command(SE)
            )

    def process_rawq(self) -> None:
        """
        Processes the data in the raw queue: removes the Telnet commands,
        answers the option negotiation, and passes the decoded text to the
        callback. Keeps an incomplete command in the raw queue until more data
        arrives, so it never blocks.
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
        if text and self.data_callback is not None:
            self.data_callback(text)

    def fill_rawq(self) -> None:
        """
        Reads once from the socket into the raw queue. Blocks if no data is
        available, and sets eof when the connection was closed.
        """
        data = cast(socket.socket, self.sock).recv(_READ_SIZE)
        self.msg('Recv: %r', data)
        self.eof = not data
        self.rawq += data

    def receive(self, timeout: float | None) -> bool | None:
        """
        Waits for data, reads it once and passes the received text to the
        callback.

        :type  timeout: float|None
        :param timeout: The maximum time to wait, in seconds; None waits
            without limit.
        :rtype:  bool|None
        :return: True if data was received, None if the time ran out, False
            if the connection was closed.
        """
        if self.eof:
            return False
        cast(socket.socket, self.sock).settimeout(timeout)
        try:
            self.fill_rawq()
        except (TimeoutError, BlockingIOError):  # BlockingIOError: timeout 0
            return None
        finally:
            if self.sock:
                self.sock.settimeout(self.connect_timeout)  # for sendall()
        self.process_rawq()
        return not self.eof
