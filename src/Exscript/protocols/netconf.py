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
SSH2 Netconf support, based on ncclient and paramiko.
"""

import codecs
import contextlib
import contextvars
import functools
import inspect
import logging
import re
import threading
import time
from collections.abc import Callable, Iterator, Mapping
from typing import TYPE_CHECKING, Any, NoReturn, Self, cast

from paramiko.ssh_exception import SSHException

from ..util.xml import XMLValidationError, _parse, validate_xml
from .exception import (
    LoginFailure,
    ProtocolException,
    RPCError,
)
from .ssh2 import SSH2

if TYPE_CHECKING:
    from lxml.etree import _Element
    from paramiko import Channel, Transport

    from ..account import Account
    from ..util.impl import _Context

# ncclient and lxml are imported when the first NETCONF session starts, not
# with Exscript: lxml enables the GIL of free-threaded Python.

_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())

# Matches a NETCONF 1.1 chunk header: LF HASH chunk-size LF (RFC 6242 §4.2).
_chunk_header_re = re.compile(rb'\n#(\d+)\n')
_end_of_chunks_re = re.compile(rb'\n##\n')

# The framing of NETCONF messages (RFC 6242): 1.0 ends each message with
# ]]>]]> (section 4.3); 1.1 sends chunks, each with a header of its size,
# and ends the message with \n##\n (section 4.2).
_EOM = b']]>]]>'
_frame_re = re.compile(rb'\n#([1-9][0-9]{0,9})\n|\n##\n')
_MAX_FRAME_HEADER = len(b'\n#4294967295\n')
_MAX_CHUNK_SIZE = 4294967295


class _Framer:
    """
    Splits the data of a NETCONF session into its messages, framed as RFC
    6242 describes, and passes each message to ncclient as text, decoded as
    UTF-8 when it is complete; bytes that are no UTF-8 become U+FFFD.
    ncclient's IO thread calls parse() with the data of each read, as with
    its own parsers.

    Workaround for ncclient 0.7.1 (the latest release): its DefaultXMLParser
    decodes the data before the message is complete, from the position of
    the last search for ]]>]]> (NETCONF 1.0) and chunk by chunk (NETCONF
    1.1). A character whose bytes arrive in two reads, or that a device
    splits across two chunks, raises a UnicodeDecodeError in the IO thread,
    which ends the session. Remove this class when ncclient frames the
    messages on bytes (https://github.com/ncclient/ncclient/issues/671), and
    let _init_ncclient() keep the parser of ncclient again
    (session.parser = device_handler.get_xml_parser(session)).
    """

    def __init__(self, session: Any) -> None:
        """
        Constructor.

        :param session: ncclient's SSHSession, which gets the messages.
        """
        from ncclient.transport.session import NetconfBase

        self._session = session
        self._base_11 = NetconfBase.BASE_11
        self._data = bytearray()
        self._chunks: list[bytes] = []  # of the NETCONF 1.1 message being received
        self._searched = 0  # NETCONF 1.0: the data before this has no ]]>]]>

    def parse(self, data: bytes) -> None:
        """
        Takes the data of a read, and passes the messages that are complete
        to ncclient, in their order.

        :raises NetconfFramingError: (of ncclient) If the data breaks the
            chunked framing of NETCONF 1.1.
        """
        self._data += data
        while (message := self._next_message()) is not None:
            text = message.decode('utf-8', errors='replace').strip()
            if text:
                self._session._dispatch_message(text)

    def _next_message(self) -> bytes | None:
        """
        Removes the next complete message from the data and returns it
        without its framing, or None if no message is complete. Uses the
        framing of NETCONF 1.1 once ncclient selects it after the <hello>
        messages.
        """
        if self._session._base == self._base_11:
            return self._next_chunked_message()
        end = self._data.find(_EOM, self._searched)
        if end < 0:
            self._searched = max(0, len(self._data) - len(_EOM) + 1)
            return None
        message = bytes(self._data[:end])
        del self._data[: end + len(_EOM)]
        self._searched = 0
        return message

    def _next_chunked_message(self) -> bytes | None:
        """
        Like _next_message(), for the chunked framing of NETCONF 1.1. Skips
        whitespace between messages, e.g. behind the ]]>]]> of the <hello>
        of a server.
        """
        data = self._data
        pos = 0
        if not self._chunks:
            while pos + 1 < len(data) and data[pos] in b' \t\r\n' and data[pos + 1] != ord('#'):
                pos += 1
        try:
            while True:
                match = _frame_re.match(data, pos)
                if match is None:
                    rest = bytes(data[pos : pos + _MAX_FRAME_HEADER])
                    if len(rest) == _MAX_FRAME_HEADER or b'\n' in rest[1:]:
                        self._framing_error(rest)
                    return None  # the header is not complete
                if match.group(1) is None:  # \n##\n ends the message
                    if not self._chunks:
                        self._framing_error(match.group())
                    pos = match.end()
                    message = b''.join(self._chunks)
                    self._chunks = []
                    return message
                size = int(match.group(1))
                if size > _MAX_CHUNK_SIZE:
                    self._framing_error(match.group())
                if match.end() + size > len(data):
                    return None  # the chunk is not complete
                self._chunks.append(bytes(data[match.end() : match.end() + size]))
                pos = match.end() + size
        finally:
            del data[:pos]

    def _framing_error(self, data: bytes) -> NoReturn:
        """
        Raises ncclient's NetconfFramingError for the given data, which is
        not a chunk header where one must be.
        """
        from ncclient.transport.errors import NetconfFramingError

        raise NetconfFramingError('invalid NETCONF 1.1 chunk header: %r' % data)


# Exscript sends its <hello> and RPCs pretty-printed, so that they are readable
# in logs. ncclient serializes them with the to_xml() of two of its modules, in
# the thread that sends; _install_to_xml() replaces it with a function that
# pretty-prints only within _pretty(), so other users of ncclient in the
# process are not affected.
_pretty_print = contextvars.ContextVar('exscript_netconf_pretty_print', default=False)


@functools.cache
def _install_to_xml() -> Callable[..., str]:
    """
    Replaces to_xml() in the two ncclient modules that serialize the
    <hello> and the RPCs with a wrapper that pretty-prints within _pretty().
    Runs once per process, and returns the wrapper.
    """
    import ncclient.operations.rpc
    import ncclient.transport.session
    from ncclient.xml_ import to_xml

    @functools.wraps(to_xml)
    def _to_xml(*args: Any, **kwargs: Any) -> str:
        if _pretty_print.get():
            kwargs['pretty_print'] = True
        return cast(str, to_xml(*args, **kwargs))  # ncclient is untyped

    ncclient.operations.rpc.to_xml = _to_xml
    ncclient.transport.session.to_xml = _to_xml
    return _to_xml


@contextlib.contextmanager
def _pretty() -> Iterator[None]:
    """
    Makes the to_xml() wrapper of _install_to_xml() pretty-print within this
    context, in the current thread or task only.
    """
    token = _pretty_print.set(True)
    try:
        yield
    finally:
        _pretty_print.reset(token)


class Netconf(SSH2):
    """
    The SSH Netconf protocol adapter, based on the SSH2 adapter and ncclient.
    It always uses UTF-8, which RFC 6241 requires for all NETCONF messages,
    whatever encoding is passed.
    """

    def __init__(self, **kwargs: Any) -> None:
        """
        Constructor. Takes the keyword arguments of :class:`Protocol`.
        """
        SSH2.__init__(self, **kwargs)
        self.encoding = 'utf-8'
        # Module-Level
        self._logger = _logger
        # Internals; the ncclient objects are Any, because ncclient is untyped
        self._ncc_device_handler: Any = None
        self._ncc_session: Any = None
        self._ncc_manager: Any = None
        self._ncc_response: Any = None
        self._huge_tree = False
        self._receives_echo = False  # Netconf does not echo the sent RPC.
        self._replicate = False

    @property
    def huge_tree(self) -> bool:
        """Whether huge_tree XML parsing is enabled for RPC replies (default: False).

        Enabling this disables lxml's security limits for very large XML documents.
        See the lxml documentation for details and associated risks.
        """
        return self._huge_tree

    @huge_tree.setter
    def huge_tree(self, value: bool) -> None:
        self._huge_tree = value
        if self._ncc_manager is not None:
            self._ncc_manager.huge_tree = value

    def autoinit(self) -> None:
        """Netconf does not support terminal/shell initialization."""
        pass

    def get_prompt(self) -> list[re.Pattern[str]]:
        """
        Returns the regular expressions that match the end of a NETCONF
        message: the prompt set with set_prompt(), else the netconf_prompt_re
        of the driver.
        """
        if self._manual_prompt_re:
            return self._manual_prompt_re
        return self.get_driver().netconf_prompt_re

    def get_error_prompt(self) -> list[re.Pattern[str]]:
        """
        Returns the regular expressions that are used to monitor the response
        for errors: the pattern set with set_error_prompt(), else the
        netconf_error_re of the driver, which matches an `<rpc-error>` tag.
        """
        if self._manual_error_re:
            return self._manual_error_re
        return self.get_driver().netconf_error_re

    def get_client_capabilities(self) -> list[str] | None:
        """
        Returns the client capabilities sent in the `<hello>` message, or
        None if no NETCONF session is open.
        """
        if self._ncc_manager is None:
            return None
        return list(self._ncc_manager.client_capabilities)

    def get_server_capabilities(self) -> list[str] | None:
        """
        Returns the server capabilities received in the `<hello>` message, or
        None if no NETCONF session is open.
        """
        if self._ncc_manager is None:
            return None
        return list(self._ncc_manager.server_capabilities)

    def get_session_id(self) -> str | None:
        """
        Returns the session ID received in the `<hello>` message, or None
        if no NETCONF session is open.
        """
        if self._ncc_manager is None:
            return None
        return str(self._ncc_manager.session_id)

    def get_response_element(self) -> '_Element | None':
        """
        Returns the parsed XML element tree of the latest RPC reply. This might
        be also some transformed XML structure, depending on specific device
        handler implementations (look for `transform_reply()` definitions).

        This is coupled to the existence of a valid plaintext response in
        self.response to enforce correct usage of the send()/execute() API.
        Therefore this method could also return `None`.

        .. HINT::
            The first call after the login will not return the received `<hello>`
            element tree although it is available as a plaintext response! This
            is by design. Please use the get_server_capabilities() method to
            access a parsed list of hello capabilities instead.

        :rtype: lxml.etree._Element | None
        """
        from ncclient.operations.rpc import RPCReply
        from ncclient.xml_ import NCElement

        if self.response is None:
            return None  # send() was called without expect_prompt()
        if isinstance(self._ncc_response, RPCReply):
            return _parse(self._ncc_response.xml, huge_tree=self.huge_tree)
        if isinstance(self._ncc_response, NCElement):
            return _parse(self._ncc_response.data_xml, huge_tree=self.huge_tree)
        return None

    @staticmethod
    def cleanup_response(
        response: str | None,
        *,
        strip_command: bool = False,
        strip_chars: str = '\x00\x07\x08',
        strip_ansi: bool = True,
    ) -> str:
        """
        Returns a clean copy of the given plaintext response, like
        :meth:`Protocol.cleanup_response`, but strip_command is ignored: the
        first line is never removed, because NETCONF does not echo the RPC.
        """
        # Netconf does not echo any commands, so there is nothing to strip.
        return SSH2.cleanup_response(
            response,
            strip_command=False,
            strip_chars=strip_chars,
            strip_ansi=strip_ansi,
        )

    def _paramiko_channel(self) -> None:
        """
        Opens a channel with the NETCONF subsystem. Tries the subsystem names
        of the ncclient device handler for the netconf_device_params of the
        driver, in order, and keeps the handler for the session.

        :raises LoginFailure: If no subsystem can be opened.
        """
        # This is a bit different from the SSH2 adapter. Here we need to init
        # the Netconf subsystem. We integrate ncclient's device params in the
        # drivers to support customization.
        from ncclient.manager import make_device_handler

        driver = self.get_driver()
        device_handler = make_device_handler(driver.netconf_device_params)
        subsystems = device_handler.get_ssh_subsystem_names()
        for subname in subsystems:
            try:
                self._channel = cast('Transport', self._transport).open_session()
                self._channel.invoke_subsystem(subname)
                self._channel.set_name("%s-subsystem-%s" % (subname, self._channel.get_id()))
            except SSHException as e:
                msg = 'Failed to open a channel with %s subsystem. (%s)'
                self._dbg(1, msg % (repr(subname), e))
                if self._channel:
                    self._channel.close()
                    self._channel = None
            else:
                self._ncc_device_handler = device_handler
                return
        msg = 'Failed to open a channel with any subsystem: ' + ', '.join(subsystems)
        raise LoginFailure(msg)

    def _init_ncclient(self) -> None:
        """
        Starts the NETCONF session with ncclient on the open channel, unless
        the manager exists already: exchanges the `<hello>` messages, starts
        ncclient's IO thread and manager, and passes the data of the session
        to the logs and the events, and its messages to the buffer. Then
        updates the driver from the server capabilities and consumes the
        server `<hello>` from the buffer.
        """
        # Bypasses ncclient's default SSH connection flow by injecting the
        # already-authenticated paramiko transport and the open NETCONF channel
        # directly into a fresh SSHSession, then calling _post_connect() to
        # complete the <hello> exchange and start ncclient's IO thread.
        if self._ncc_manager:
            return
        from ncclient.manager import Manager
        from ncclient.operations.rpc import RaiseMode
        from ncclient.transport.session import SessionListener
        from ncclient.transport.ssh import SSHSession

        _install_to_xml()
        self._dbg(1, 'Initialize ncclient and hand over channel ownership.')

        # Build a bare SSHSession — no connect() call, we inject everything.
        device_handler = self._ncc_device_handler
        session = SSHSession(device_handler)
        session._host = self.host
        session._transport = self._transport
        session._channel = self._channel
        session._channel_id = cast('Channel', self._channel).get_id()
        session._channel_name = cast('Channel', self._channel).get_name()
        session._connected = True
        session._closing.clear()
        session.parser = _Framer(session)  # see _Framer: a workaround for ncclient

        # Every message that ncclient receives also reaches the buffer. An
        # ncclient listener must be a SessionListener; its methods are replaced
        # here, so this module imports ncclient only when a session starts.
        listener = SessionListener()
        listener.callback = lambda root, raw: self._receive_message(raw)
        listener.errback = lambda error: None  # the end of the channel ends expect()
        session.add_listener(listener)

        self._wrap_channel(cast('Channel', self._channel))

        # Starts IO thread, sends client <hello>, consumes server <hello>.
        self._buffer.clear()  # keeps the first self.response clean
        with _pretty():
            session._post_connect(self.get_timeout())

        # Finally the manager is in charge of the channel.
        self._ncc_session = session
        self._ncc_manager = Manager(
            session,
            device_handler,
            timeout=self.get_timeout(),
            raise_mode=RaiseMode.NONE,  # raising custom RPCError later...
        )
        self._ncc_manager.huge_tree = self.huge_tree  # ensure synced flags

        # Exscript needs to finalize the initialization.
        self._os_guesser.check_netconf_capabilities(self.get_server_capabilities())
        self._update_auto_driver()
        self.expect_prompt()  # consumes the server <hello> from the buffer

    def _wrap_channel(self, channel: 'Channel') -> None:
        """
        Wraps recv() and send() of the given channel, which ncclient's IO
        thread calls, so the data of the session also reaches the logs, the
        standard output and the events, as it is sent and received, with its
        framing. The data is decoded as UTF-8 with an incremental decoder per
        direction, so a character that spans two reads or writes is decoded,
        too; bytes that are no UTF-8 become U+FFFD.
        """
        # Controls the behavior of the replication wrappers. The replication is
        # needed as ncclient owns the channel within its IO thread. So we need
        # to somehow fetch this raw data for display and logging. The end of the
        # received data also ends the replication of the messages to the buffer.
        self._replicate = True
        recv_decoder = codecs.getincrementaldecoder('utf-8')(errors='replace')
        send_decoder = codecs.getincrementaldecoder('utf-8')(errors='replace')

        # Setup the channel receive wrapper.
        recv = channel.recv

        @functools.wraps(recv)
        def recv_wrapper(*args: Any, **kwargs: Any) -> bytes:
            data = recv(*args, **kwargs)
            if not self._replicate:
                return data
            string_data = recv_decoder.decode(data, final=not data)
            if string_data:  # empty at the end, or for a part of a character
                self._receive_cb(string_data)
            if not data:
                self._dbg(1, 'channel.recv() returned EOF')
                self._replicate = False
            return data

        cast(Any, channel).recv = recv_wrapper  # Any: replaces a method

        # Setup the channel send wrapper. This is needed as Netconf does not
        # echo the sent data back to the client known from CLI shells.
        send = channel.send
        param = next(iter(inspect.signature(send).parameters))  # first param

        @functools.wraps(send)
        def send_wrapper(*args: Any, **kwargs: Any) -> int:
            count = send(*args, **kwargs)
            if not self._replicate:
                return count
            data = kwargs[param] if param in kwargs else args[0]
            string_data = ''
            if count is None:
                string_data = send_decoder.decode(data)
            elif count > 0:
                string_data = send_decoder.decode(data[:count])
            else:
                self._dbg(1, 'channel.send() returned EOF')
                self._replicate = False
            if string_data:  # empty for a part of a character
                self._send_cb(string_data)
            return count

        cast(Any, channel).send = send_wrapper  # Any: replaces a method

    def _receive_message(self, message: str) -> None:
        """
        Appends a message that ncclient's IO thread received, without its
        framing, to the buffer, followed by the ]]>]]> that the prompt
        matches; so the response has no framing, and a prompt never matches
        within a message. Does nothing after the end of the received data.
        """
        if self._replicate:
            self._buffer.append(message + ']]>]]>')

    def login(
        self,
        account: 'Account | _Context | None' = None,
        app_account: 'Account | _Context | None' = None,
        flush: bool = True,
    ) -> None:
        """
        Logs into the host like :meth:`Protocol.login`, with the account and
        account factory rules described there. NETCONF authenticates at the
        protocol level only and then starts the NETCONF session; there is no
        app-level login, so the driver's auto-authorization is skipped and
        app_account and flush have no effect. The app-level authentication
        and authorization are marked as done.

        :param account: The account for protocol level authentication.
        :param app_account: Not used by NETCONF.
        :param flush: Not used by NETCONF.
        """
        # Simplified procedure for Netconf to suppress driver auto-authorize.
        with self._get_account(account) as account:
            if app_account is None:
                app_account = account
            self.authenticate(account, app_account, flush=False)
            self.app_authorize()  # just to set the flag

    def authenticate(
        self,
        account: 'Account | _Context | None' = None,
        app_account: 'Account | _Context | None' = None,
        flush: bool = True,
    ) -> None:
        """
        Like :meth:`Protocol.authenticate`, and then starts the NETCONF
        session on the authenticated connection: exchanges the `<hello>`
        messages and consumes the server `<hello>` from the buffer.
        app_account and flush have no effect, because NETCONF has no
        app-level authentication.

        :param account: The account for protocol level authentication.
        :param app_account: Not used by NETCONF.
        :param flush: Not used by NETCONF.
        """
        super().authenticate(account, app_account, flush=flush)
        # Authentication is complete and the subsystem channel is open. The
        # server <hello> waits unread in the channel buffer. Hand the channel to
        # ncclient now — it will consume the <hello> and start its IO thread.
        self._init_ncclient()

    def app_authenticate(
        self,
        account: 'Account | _Context | None' = None,
        flush: bool = True,
        bailout: bool = False,
    ) -> None:
        """
        Netconf does not support app-authentication. Only marks it as done,
        so is_app_authenticated() returns True; the arguments are not used.
        """
        self._app_authenticated = True

    def app_authorize(
        self,
        account: 'Account | _Context | None' = None,
        flush: bool = True,
        bailout: bool = False,
    ) -> None:
        """
        Netconf does not support app-authorization. Only marks it as done,
        so is_app_authorized() returns True; the arguments are not used.
        """
        self._app_authorized = True

    def auto_app_authorize(
        self,
        account: 'Account | _Context | None' = None,
        flush: bool = True,
        bailout: bool = False,
    ) -> None:
        """
        Netconf does not support app-authorization. Like app_authorize(),
        only marks it as done; the arguments are not used.
        """
        self.app_authorize()  # just to set the flag

    @staticmethod
    def reassemble_chunks(response: str) -> str:
        """
        Reassembles a NETCONF 1.1 chunked response into plain content.

        Each chunk is introduced by a header `LF HASH chunk-size LF` where the
        size is the exact byte count of the following chunk (RFC 6242 §4.2),
        in the UTF-8 encoding of the response.
        The end-of-chunks marker `LF HASH HASH LF` gets stripped finally. The
        response and the buffer of the adapter have no framing; this is
        useful for the received data of the logs and data_received_event.

        Raises ValueError on unexpected trailing bytes after the last chunk.

        :param response: The chunked response to reassemble.
        :rtype: str
        :return: The reassembled response.
        """
        if not response.startswith('\n#'):  # spares encoding other responses
            return response
        data = response.encode('utf-8')
        match = _chunk_header_re.match(data)
        if not match:
            return response
        parts = []
        while match:
            start = match.end()  # after the chunk header
            end = start + int(match.group(1))  # exactly size bytes of content
            parts.append(data[start:end])
            match = _chunk_header_re.match(data, end)
        data = data[end:]
        if data:
            # Internally this would be already consumed as the prompt.
            match = _end_of_chunks_re.match(data)
            if match:
                data = data[match.end() :]  # consume the end-of-chunks marker
        if data:
            # This should only happen if we have internal issues with the prompt
            # or buffer handling before this reassembly is called. ncclient
            # should have caught buggy devices already at the transport layer.
            msg = 'Unexpected trailing bytes after chunk reassembly: %s'
            raise ValueError(msg % repr(data[:50].decode('utf-8', 'replace') + '...'))
        return b''.join(parts).decode('utf-8')

    def _fill_buffer(self, timeout: float | None) -> bool | None:
        """
        Waits until ncclient's IO thread has appended data to the buffer, for
        up to the given time. Returns True if data arrived, None if the time
        ran out, and False if the channel was closed.
        """
        # ncclient's thread reads the channel and appends to the buffer (see the
        # recv wrapper in _init_ncclient()), so this only waits for new data.
        size = self._buffer.size()
        deadline = None if timeout is None else time.monotonic() + timeout
        while self._buffer.size() == size:
            if not self._replicate:  # the channel was closed
                return False
            if deadline is not None and time.monotonic() >= deadline:
                return None
            time.sleep(0.01)
        return True

    def _send(self, data: str) -> None:
        """
        Validates the given RPC body, sends it as an RPC with ncclient, and
        waits for the reply, which is kept for get_response_element(). The
        recv() and send() wrappers of the channel pass the data to the buffer
        and the events.

        :raises XMLValidationError: If the RPC body is not valid XML, or not
            one XML element.
        :raises TimeoutException: If no reply arrives in time.
        :raises ConnectionClosedException: If the server closed the session,
            also before the RPC.
        :raises ProtocolException: On other errors of ncclient.
        """
        from lxml.etree import XMLSyntaxError
        from ncclient import NCClientError
        from ncclient.operations.errors import TimeoutExpiredError
        from ncclient.transport.errors import SessionCloseError

        self._ncc_response = None
        self._validate_rpc_body(data)
        try:
            element = _parse(data)
        except XMLSyntaxError as exc:  # valid within <rpc>, so e.g. two elements or text
            raise XMLValidationError(
                'XML validation of the RPC command has failed: the RPC body must be one '
                f'XML element. The error was caused by:\n{type(exc).__name__}: {exc}',
                xmlstring=data,
            )
        try:
            self._ncc_manager.timeout = self.get_timeout()  # set_timeout() may have changed it
            with _pretty():
                self._ncc_response = self._ncc_manager.dispatch(element)
            # wrappers handle the self.data_sent_event
        except TimeoutExpiredError:
            self._raise_on_response_timeout()
        except NCClientError as e:
            # ncclient reads the end of the session, or refuses to send after it.
            if isinstance(e, SessionCloseError) or not self._ncc_session.connected:
                self._raise_on_response_eof()
            msg = 'ncclient related error (%s)' % str(e)
            raise ProtocolException(msg)
        except Exception:
            self._dbg(1, 'Error while writing to connection')
            raise
        self._dbg(4, 'Received response type: %s' % type(self._ncc_response).__name__)

    def _validate_rpc_body(self, data: str) -> None:
        """
        Checks that the given RPC body, wrapped in an `<rpc>` element, is
        valid XML, and raises XMLValidationError if not.
        """
        from lxml.etree import XMLSyntaxError

        _wrapper_start_tag = '<rpc>\n'
        _wrapper_end_tag = '\n</rpc>'
        data = f'{_wrapper_start_tag}{data}{_wrapper_end_tag}'
        try:
            validate_xml(data, silent=False)
        except UnicodeEncodeError as exc:
            # Fix the absolute character offsets.
            exc.start -= len(_wrapper_start_tag)
            exc.end -= len(_wrapper_start_tag)
            raise XMLValidationError(
                'XML validation of the RPC command has failed. '
                f'The error was caused by:\n{type(exc).__name__}: {exc}',
                xmlstring=data,
            )
        except XMLSyntaxError as exc:
            err = XMLValidationError(
                'XML validation of the RPC command has failed. '
                f'The error was caused by:\n{type(exc).__name__}: {exc}',
                xmlstring=data,
            )
            err.add_note(
                'Note: Reported line numbers are shifted by +1 due to the '
                'synthetic <rpc>\\n...\\n</rpc> wrapper used for validation.'
            )
            raise err

    def _raise_on_response_with_errors(self, line: str) -> None:
        """
        Raises RPCError if the latest RPC reply has an `<rpc-error>` with the
        severity error. The matched line is not used: the error comes from
        the reply that ncclient parsed.
        """
        # For device handlers that apply XSLT (e.g. Junos) or any transformation,
        # dispatch() returns NCElement instead of RPCReply.
        response = self._ncc_response
        rpc_reply = getattr(response, '_NCElement__result', response)
        for error in rpc_reply.errors:
            if error.severity == 'error':
                raise RPCError._from_ncclient(rpc_reply.errors)

    def _interact(
        self,
        key_handlers: Mapping[str, Callable[[Self], object]] | None = None,
        handle_window_size: bool = True,
    ) -> NoReturn:
        """
        Raises NotImplementedError: NETCONF has no interactive shell.
        """
        # Netconf does not support interactive shells. User should use
        # native `ssh HOST -p 830 -s netconf` for an interactive session.
        raise NotImplementedError()

    def _logout(self) -> None:
        """
        Closes the NETCONF session with a `<close-session>` RPC; errors are
        ignored.
        """
        try:
            self._ncc_manager.timeout = self.get_timeout()
            with _pretty():
                self._ncc_manager.close_session()
        except Exception:
            pass

    def _close(self, force: bool = False) -> None:
        """
        Tells ncclient's IO thread that the session is closed on purpose,
        closes the transport, and waits up to a second for the IO thread to
        end. Then closes the socket like SSH2._close(), and the channel if the
        IO thread ended; else the thread ends when its listener returns.
        """
        # Clear the ncclient manager reference.
        if self._ncc_manager:
            self._ncc_manager = None

        # Signal ncclient's IO thread that this is an intentional close.
        # Must happen before the transport is closed so the thread treats the
        # subsequent empty recv() as expected (breaks cleanly, no SessionCloseError).
        ncc_session = self._ncc_session
        if self._ncc_session:
            try:
                self._ncc_session._closing.set()
            except Exception:
                pass
            self._ncc_session = None

        # Disable the replication wrappers.
        self._replicate = False

        # Like ncclient's SSHSession.close(), close the transport first: paramiko
        # then marks the channel closed and makes the pipe that the IO thread
        # selects on readable, so the thread reads b'' and ends. Closing the
        # channel first, as SSH2._close() does, closes that pipe, so the thread
        # would never wake up again.
        if self._transport:
            self._transport.close()

        # Wait for ncclient's IO thread to end, unless this is that thread, e.g.
        # in a monitor callback.
        if ncc_session and ncc_session is not threading.current_thread():
            ncc_session.join(timeout=1)
            if ncc_session.is_alive():
                self._dbg(1, "ncclient's IO thread did not end within a second.")

        # If the thread still runs a listener, e.g. a slow monitor callback, or
        # this is that thread, leave the channel open: closing it would close the
        # pipe that the thread selects on, so the thread would never see the end
        # of the session and would wake up every 0.1 seconds until the process
        # ends. The pipe stays readable, so the thread ends by itself once the
        # listener returns; paramiko closes the channel when it is
        # garbage-collected.
        if ncc_session and ncc_session.is_alive():
            self._channel = None

        # SSH2 closes the paramiko channel, the transport, and the socket.
        super()._close(force=force)
