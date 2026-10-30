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

import functools
import inspect
import logging
import re
import time

from lxml.etree import XMLSyntaxError
from ncclient import NCClientError
from ncclient.manager import Manager, make_device_handler
from ncclient.operations.errors import TimeoutExpiredError
from ncclient.operations.rpc import RaiseMode, RPCReply
from ncclient.transport.ssh import SSHSession
from ncclient.xml_ import NCElement, to_ele, to_xml
from paramiko.ssh_exception import SSHException

from ..util.xml import XMLValidationError, validate_xml
from .exception import (
    LoginFailure,
    ProtocolException,
    RPCError,
)
from .ssh2 import SSH2

_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())

# Matches a NETCONF 1.1 chunk header: LF HASH chunk-size LF (RFC 6242 §4.2).
_chunk_header_re = re.compile(r'\n#(\d+)\n')
_end_of_chunks_re = re.compile(r'\n##\n')


class Netconf(SSH2):
    """
    The SSH Netconf protocol adapter, based on the SSH2 adapter and ncclient.
    """

    def __init__(self, **kwargs):
        SSH2.__init__(self, **kwargs)
        # Module-Level
        self._logger = _logger
        # Internals
        self._ncc_device_handler = None
        self._ncc_session = None
        self._ncc_manager = None
        self._ncc_response = None
        self._huge_tree = False
        self._receives_echo = False  # Netconf does not echo the sent RPC.
        self._replicate = False

    @property
    def huge_tree(self):
        """Whether huge_tree XML parsing is enabled for RPC replies (default: False).

        Enabling this disables lxml's security limits for very large XML documents.
        See the lxml documentation for details and associated risks.
        """
        return self._huge_tree

    @huge_tree.setter
    def huge_tree(self, value):
        self._huge_tree = value
        if self._ncc_manager is not None:
            self._ncc_manager.huge_tree = value

    def autoinit(self):
        """Netconf does not support terminal/shell initialization."""
        pass

    def get_prompt(self):
        if self._manual_prompt_re:
            return self._manual_prompt_re
        return self.get_driver().netconf_prompt_re

    def get_error_prompt(self):
        if self._manual_error_re:
            return self._manual_error_re
        return self.get_driver().netconf_error_re

    def get_client_capabilities(self):
        """Returns the client capabilities sent in the `<hello>` message."""
        if self._ncc_manager is None:
            return None
        return list(self._ncc_manager.client_capabilities)

    def get_server_capabilities(self):
        """Returns the server capabilities received in the `<hello>` message."""
        if self._ncc_manager is None:
            return None
        return list(self._ncc_manager.server_capabilities)

    def get_session_id(self):
        """Returns the session ID received in the `<hello>` message."""
        if self._ncc_manager is None:
            return None
        return str(self._ncc_manager.session_id)

    def get_response_element(self):
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

        :rtype: lxml.etree.Element | None
        """
        if self.response is None:
            return None  # send() was called without expect_prompt()
        if isinstance(self._ncc_response, RPCReply):
            return to_ele(self._ncc_response.xml, huge_tree=self.huge_tree)
        if isinstance(self._ncc_response, NCElement):
            return to_ele(self._ncc_response.data_xml, huge_tree=self.huge_tree)
        return None

    @staticmethod
    def cleanup_response(
        response, *, strip_command=False, strip_chars='\x00\x07\x08', strip_ansi=True
    ):
        # Netconf does not echo any commands, so there is nothing to strip.
        return SSH2.cleanup_response(
            response,
            strip_command=False,
            strip_chars=strip_chars,
            strip_ansi=strip_ansi,
        )

    def _paramiko_channel(self):
        # This is a bit different from the SSH2 adapter. Here we need to init
        # the Netconf subsystem. We integrate ncclient's device params in the
        # drivers to support customization.
        driver = self.get_driver()
        device_handler = make_device_handler(driver.netconf_device_params)
        subsystems = device_handler.get_ssh_subsystem_names()
        for subname in subsystems:
            try:
                self._channel = self._transport.open_session()
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

    def _init_ncclient(self):
        # Bypasses ncclient's default SSH connection flow by injecting the
        # already-authenticated paramiko transport and the open NETCONF channel
        # directly into a fresh SSHSession, then calling _post_connect() to
        # complete the <hello> exchange and start ncclient's IO thread.
        if self._ncc_manager:
            return
        self._dbg(1, 'Initialize ncclient and hand over channel ownership.')

        # Build a bare SSHSession — no connect() call, we inject everything.
        device_handler = self._ncc_device_handler
        session = SSHSession(device_handler)
        session._host = self.host
        session._transport = self._transport
        session._channel = self._channel
        session._channel_id = self._channel.get_id()
        session._channel_name = self._channel.get_name()
        session._connected = True
        session._closing.clear()

        # Controls the behavior of the replication wrappers. The replication is
        # needed as ncclient owns the channel within its IO thread. So we need
        # to somehow fetch this raw data for display, logging and raw response
        # buffering/matching.
        self._replicate = True

        # Setup the channel receive wrapper.
        recv = self._channel.recv

        @functools.wraps(recv)
        def recv_wrapper(*args, **kwargs):
            data = recv(*args, **kwargs)
            if not self._replicate:
                return data
            if data:
                string_data = data.decode(self.encoding)
                self._receive_cb(string_data)
                self._buffer.append(string_data)
            else:
                self._dbg(1, 'channel.recv() returned EOF')
                self._replicate = False
            return data

        self._channel.recv = recv_wrapper

        # Setup the channel send wrapper. This is needed as Netconf does not
        # echo the sent data back to the client known from CLI shells.
        send = self._channel.send
        param = next(iter(inspect.signature(send).parameters))  # first param

        @functools.wraps(send)
        def send_wrapper(*args, **kwargs):
            count = send(*args, **kwargs)
            if not self._replicate:
                return count
            data = kwargs[param] if param in kwargs else args[0]
            if count is None:
                string_data = data.decode(self.encoding)
                self._send_cb(string_data)
            elif count > 0:
                string_data = data[:count].decode(self.encoding)
                self._send_cb(string_data)
            else:
                self._dbg(1, 'channel.send() returned EOF')
                self._replicate = False
            return count

        self._channel.send = send_wrapper

        # Setup the RPC relevant to_xml wrapper so that ncclient's RPCs are
        # always send (and logged by Exscript) in a pretty formatted style.
        # This is quite hacky, but the only way to achieve it on the fly
        # without additional XML parsing and reformatting.
        import ncclient.operations.retrieve as retrieve_module
        import ncclient.operations.rpc as rpc_module
        import ncclient.transport.session as session_module

        @functools.wraps(to_xml)
        def to_xml_wrapper(*args, **kwargs):
            kwargs['pretty_print'] = True
            return to_xml(*args, **kwargs)

        retrieve_module.to_xml = to_xml_wrapper  # for retrieved RPC replies
        rpc_module.to_xml = to_xml_wrapper  # for all kinds of sent RPCs
        session_module.to_xml = to_xml_wrapper  # where client hello is build

        # Starts IO thread, sends client <hello>, consumes server <hello>.
        self._buffer.clear()  # keeps the first self.response clean
        session._post_connect(self.get_timeout())

        # Selects the driver/device-specific XML parser for all subsequent RPCs.
        session.parser = device_handler.get_xml_parser(session)

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

    def login(self, account=None, app_account=None, flush=True):
        # Simplified procedure for Netconf to suppress driver auto-authorize.
        with self._get_account(account) as account:
            if app_account is None:
                app_account = account
            self.authenticate(account, app_account, flush=False)
            self.app_authorize()  # just to set the flag

    def authenticate(self, account=None, app_account=None, flush=True):
        super().authenticate(account, app_account, flush=flush)
        # Authentication is complete and the subsystem channel is open. The
        # server <hello> waits unread in the channel buffer. Hand the channel to
        # ncclient now — it will consume the <hello> and start its IO thread.
        self._init_ncclient()

    def app_authenticate(self, account=None, flush=True, bailout=False):
        """Netconf does not support app-authentication."""
        self._app_authenticated = True

    def app_authorize(self, account=None, flush=True, bailout=False):
        """Netconf does not support app-authorization."""
        self._app_authorized = True

    def auto_app_authorize(self, account=None, flush=True, bailout=False):
        """Netconf does not support app-authorization."""
        self.app_authorize()  # just to set the flag

    @staticmethod
    def reassemble_chunks(response):
        """
        Reassembles a NETCONF 1.1 chunked response into plain content.

        Each chunk is introduced by a header `LF HASH chunk-size LF` where the
        size is the exact byte count of the following chunk (RFC 6242 §4.2).
        The end-of-chunks marker `LF HASH HASH LF` gets stripped finally. Useful
        to also reassemble chunks in received data from events.

        Raises ValueError on unexpected trailing bytes after the last chunk.

        :param response: The chunked response to reassemble.
        :rtype: str
        :return: The reassembled response.
        """
        match = _chunk_header_re.match(response)
        if not match:
            return response
        assembled = ''
        while match:
            size = int(match.group(1))
            response = response[match.end() :]  # consume the chunk header
            assembled += response[:size]  # extract exactly size chars of content
            response = response[size:]  # consume the chunk content
            match = _chunk_header_re.match(response)
        if response:
            # Internally this would be already consumed as the prompt.
            match = _end_of_chunks_re.match(response)
            if match:
                response = response[match.end() :]  # consume the end-of-chunks marker
        if response:
            # This should only happen if we have internal issues with the prompt
            # or buffer handling before this reassembly is called. ncclient
            # should have caught buggy devices already at the transport layer.
            msg = 'Unexpected trailing bytes after chunk reassembly: %s'
            raise ValueError(msg % repr(response[:50] + '...'))
        return assembled

    def _domatch(self, prompt, flush):
        # This mimics the behavior of CLI-driven prompt matching to keep API
        # parity with the Telnet and SSH2 adapter.
        deadline = time.monotonic() + self.get_timeout()
        while not self._expect_canceled:
            n, match, search_window = self._domatch_buffer(prompt)
            if not match:
                # This is just a safety-net as the buffer is always filled by
                # the replication wrapper and ncclient's blocking dispatch.
                if time.monotonic() > deadline:
                    self._raise_on_response_timeout()
                time.sleep(0.05)
                continue
            self.response = self._domatch_extract(match, len(search_window), flush)
            self.response = self.reassemble_chunks(self.response)
            return n, match
        self._raise_on_canceled_expect()

    def _send(self, data):
        self._ncc_response = None
        self._validate_rpc_body(data)
        try:
            element = to_ele(data)
            self._ncc_response = self._ncc_manager.dispatch(element)
            # wrappers handle the self.data_sent_event
        except TimeoutExpiredError:
            self._raise_on_response_timeout()
        except NCClientError as e:
            msg = 'ncclient related error (%s)' % str(e)
            raise ProtocolException(msg)
        except Exception:
            self._dbg(1, 'Error while writing to connection')
            raise
        self._dbg(4, 'Received response type: %s' % type(self._ncc_response).__name__)

    def _validate_rpc_body(self, data):
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

    def _raise_on_response_with_errors(self):
        # For device handlers that apply XSLT (e.g. Junos) or any transformation,
        # dispatch() returns NCElement instead of RPCReply.
        response = self._ncc_response
        rpc_reply = getattr(response, '_NCElement__result', response)
        for error in rpc_reply.errors:
            if error.severity == 'error':
                raise RPCError._from_ncclient(rpc_reply.errors)

    def _interact(self, key_handlers=None, handle_window_size=True):
        # Netconf does not support interactive shells. User should use
        # native `ssh HOST -p 830 -s netconf` for an interactive session.
        raise NotImplementedError()

    def _logout(self):
        try:
            self._ncc_manager.close_session()
        except Exception:
            pass

    def _close(self, force=False):
        # Clear the ncclient manager reference.
        if self._ncc_manager:
            self._ncc_manager = None

        # Signal ncclient's IO thread that this is an intentional close.
        # Must happen before the channel is shut down so the thread treats the
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

        # SSH2 closes the paramiko channel, transport, and socket.
        # Closing the channel causes channel.recv() to return b'', which —
        # combined with _closing being set — causes the IO thread to exit.
        super()._close(force=force)

        # Wait for ncclient's IO thread to fully terminate.
        # Must be after super() so the channel is already closed when we join.
        if ncc_session:
            try:
                ncc_session.join(timeout=0.3)
            except Exception:
                pass
