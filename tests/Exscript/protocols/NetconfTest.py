"""
Tests for the NETCONF adapter: the parts that need no server, sessions with
a small NETCONF server, and the replay of a recorded netopeer2 session.
"""

import inspect
import io
import os
import re
import subprocess
import sys
import threading
import unittest
from unittest import mock

import ncclient.operations.rpc
import ncclient.transport.session
import paramiko
from hypothesis import given, settings
from hypothesis import strategies as st
from lxml import etree
from ncclient.manager import make_device_handler
from ncclient.operations.rpc import RPC, RPCReply
from ncclient.transport.session import HelloHandler
from ncclient.transport.ssh import SSHSession
from ncclient.xml_ import NCElement, new_ele

from Exscript import Account
from Exscript.protocols import drivers, netconf
from Exscript.protocols.exception import (
    ConnectionClosedException,
    LoginFailure,
    RPCError,
    TimeoutException,
)
from Exscript.protocols.netconf import Netconf
from Exscript.util.xml import XMLValidationError

from .replay import Recording, ReplayServer, decode_messages, encode_message
from .SSH2Test import KeyServer

BASE = 'urn:ietf:params:netconf:base:1.0'
BASE_11 = 'urn:ietf:params:netconf:base:1.1'
CANDIDATE = 'urn:ietf:params:netconf:capability:candidate:1.0'
NS = 'urn:ietf:params:xml:ns:netconf:base:1.0'
EOM = b']]>]]>'
KEYFILE = os.path.join(os.path.dirname(__file__), 'id_rsa')
RECORDING = os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir, 'recordings', 'netopeer2',
    'netopeer2-netconf.jsonl',
)  # fmt: skip
GET_CONFIG = '<get-config><source><running/></source></get-config>'
LOCK = '<lock><target><running/></target></lock>'
FILTER = (
    '<get><filter type="subtree"><netconf-state '
    'xmlns="urn:ietf:params:xml:ns:yang:ietf-netconf-monitoring"><capabilities/>'
    '</netconf-state></filter></get>'
)
CLOSE = object()
_message_id = re.compile(rb'message-id="([^"]*)"')


class ReassembleChunksTest(unittest.TestCase):
    def testChunks(self):
        # The second chunk contains what looks like a chunk header.
        self.assertEqual(Netconf.reassemble_chunks('\n#5\n<ok/>\n#3\n\n#1\n##\n'), '<ok/>\n#1')

    def testWithoutChunks(self):
        self.assertEqual(Netconf.reassemble_chunks('<rpc-reply/>'), '<rpc-reply/>')

    def testTrailingBytes(self):
        self.assertRaises(ValueError, Netconf.reassemble_chunks, '\n#2\nok\n##\nx')
        self.assertRaises(ValueError, Netconf.reassemble_chunks, '\n#2\nokx')

    def testManyChunks(self):
        chunk = 'x' * 4096
        framed = ''.join('\n#4096\n' + chunk for _ in range(1024)) + '\n##\n'
        self.assertEqual(Netconf.reassemble_chunks(framed), chunk * 1024)

    def testMultibyteCharacters(self):
        # The sizes count the bytes of the UTF-8 encoding (RFC 6242, section 4.2).
        framed = '\n#6\n<a>Zü\n#15\nrich 20 €</a>\n##\n'
        self.assertEqual(Netconf.reassemble_chunks(framed), '<a>Zürich 20 €</a>')

    @settings(max_examples=200, deadline=None)
    @given(st.text(min_size=1, max_size=200), st.lists(st.integers(1, 40), max_size=12))
    def testAnyText(self, text, sizes):
        # Chunks of any size, also with text that looks like a chunk header. A
        # character that a device splits across two chunks needs the framing to
        # be parsed before the decoding, so the chunks end at characters here.
        chunks, pos = [], 0
        for size in sizes:
            chunks.append(text[pos : pos + size])
            pos += size
        chunks.append(text[pos:])
        framed = ''.join('\n#%d\n%s' % (len(c.encode()), c) for c in chunks if c) + '\n##\n'
        self.assertEqual(Netconf.reassemble_chunks(framed), text)


class NcclientContractTest(unittest.TestCase):
    """The ncclient internals that the adapter uses; an update of ncclient must keep them."""

    def setUp(self):
        self.handler = make_device_handler({'name': 'default'})

    def testSessionAttributes(self):
        # _init_ncclient() sets these on a session that it did not connect.
        session = SSHSession(self.handler)
        names = '_host', '_transport', '_channel', '_channel_id', '_channel_name', '_connected'
        for name in names:
            self.assertTrue(hasattr(session, name), name)
        self.assertIsInstance(session._closing, threading.Event)
        self.assertIn('timeout', inspect.signature(session._post_connect).parameters)
        session.parser = self.handler.get_xml_parser(session)

    def testReplyOfATransformedResult(self):
        # _raise_on_response_with_errors() reads the reply behind an NCElement.
        reply = RPCReply('<rpc-reply xmlns="%s" message-id="1"><ok/></rpc-reply>' % BASE)
        reply.parse()
        self.assertIs(NCElement(reply, lambda root: root)._NCElement__result, reply)

    def testPrettyPrintOnlyForExscript(self):
        to_xml = netconf._install_to_xml()
        self.assertIs(ncclient.operations.rpc.to_xml, to_xml)
        self.assertIs(ncclient.transport.session.to_xml, to_xml)
        rpc = RPC.__new__(RPC)  # _wrap() needs only these two attributes
        rpc._id, rpc._device_handler = '1', self.handler
        for serialize in (
            lambda: HelloHandler.build([BASE], self.handler),
            lambda: rpc._wrap(new_ele('get')),
        ):
            self.assertNotIn('\n  <', serialize())  # other ncclient users
            with netconf._pretty():
                self.assertIn('\n  <', serialize())
            self.assertNotIn('\n  <', serialize())


class LazyImportTest(unittest.TestCase):
    def testImportLoadsNoLxml(self):
        # lxml enables the GIL of free-threaded Python, so only NETCONF and RPC templates load it.
        code = 'import sys, Exscript.protocols; print([m for m in ("lxml", "ncclient") if m in sys.modules])'
        result = subprocess.run(  # noqa: S603 (constant arguments)
            [sys.executable, '-c', code], capture_output=True, text=True, check=True
        )
        self.assertEqual(result.stdout.strip(), '[]')


class NetconfTest(unittest.TestCase):
    """The adapter without a session."""

    CORRELATE = Netconf

    def setUp(self):
        self.conn = Netconf(timeout=1, connect_rate_limit=0)

    def testNoSessionInformationBeforeLogin(self):
        self.assertIsNone(self.conn.get_client_capabilities())
        self.assertIsNone(self.conn.get_server_capabilities())
        self.assertIsNone(self.conn.get_session_id())
        self.assertIsNone(self.conn.get_response_element())

    def testPrompts(self):
        driver = self.conn.get_driver()
        self.assertEqual(self.conn.get_prompt(), driver.netconf_prompt_re)
        self.assertEqual(self.conn.get_error_prompt(), driver.netconf_error_re)
        self.conn.set_prompt(r'</rpc-reply>')
        self.conn.set_error_prompt(r'<error/>')
        self.assertEqual([p.pattern for p in self.conn.get_prompt()], [r'</rpc-reply>'])
        self.assertEqual([p.pattern for p in self.conn.get_error_prompt()], [r'<error/>'])

    def testNoShell(self):
        self.conn.autoinit()  # nothing to initialize
        self.assertRaises(NotImplementedError, self.conn.interact)

    def testAppLevelAuthenticationIsNotNeeded(self):
        self.conn.app_authenticate()
        self.assertTrue(self.conn.is_app_authenticated())
        self.conn.auto_app_authorize()
        self.assertTrue(self.conn.is_app_authorized())

    def testUTF8(self):
        self.assertEqual(self.conn.encoding, 'utf-8')
        self.assertEqual(Netconf(encoding='latin-1').encoding, 'utf-8')

    def testCharactersSplitAcrossReads(self):
        received = []
        self.conn.data_received_event.connect(received.append)
        # ü and € span reads, \xff is no UTF-8, and the data ends within a character.
        channel = FakeChannel([b'<a>Z\xc3', b'\xbcrich \xe2', b'\x82', b'\xac \xff</a> \xe2\x82'])
        self.conn._wrap_channel(channel)
        while channel.recv(4096):
            pass
        text = '<a>Zürich € \ufffd</a> \ufffd'
        self.assertEqual(''.join(received), text)
        self.assertEqual(str(self.conn._buffer), text)
        self.assertEqual(self.conn.stdout.getvalue(), text)

    def testCharactersSplitAcrossWrites(self):
        sent = []
        self.conn.data_sent_event.connect(sent.append)
        channel = FakeChannel()
        self.conn._wrap_channel(channel)
        data = rest = '<a>Zürich €</a>'.encode()
        while rest:  # like ncclient, which sends the rest after a short write
            rest = rest[channel.send(rest) :]
        self.assertEqual(channel.sent, data)
        self.assertEqual(''.join(sent), '<a>Zürich €</a>')
        self.assertEqual(self.conn.stdout.getvalue(), '<a>Zürich €</a>')


class FakeChannel:
    """Returns the given pieces from recv(), then b''; send() writes two bytes at most."""

    def __init__(self, pieces=()):
        self.pieces = list(pieces)
        self.sent = b''

    def recv(self, nbytes):
        return self.pieces.pop(0) if self.pieces else b''

    def send(self, s):
        self.sent += s[:2]
        return len(s[:2])


class NetconfServer:
    """
    A NETCONF server on the netconf SSH subsystem, on 127.0.0.1 at a free port.

    :param reply: Called with each RPC (bytes) except close-session. Returns
        the content of the rpc-reply (str; bytes are sent as they are), None
        to send no reply, or CLOSE to close the session. close-session gets
        <ok/>, and then the server closes the session.
    :param capabilities: The capabilities in the hello of the server. If both
        hellos have base:1.1, the messages are framed in chunks (RFC 6242),
        else with ]]>]]>.
    :param chunk_size: Splits each message into chunks of this many bytes.
    :param piece_size: Writes the data to the channel in pieces of this many bytes.
    :param subsystem: Whether the netconf subsystem is available.
    :param channels: Whether the server opens session channels.
    :param ignore_close_session: Whether close-session gets no reply and
        leaves the session open, like on a server that hangs.
    :param banner: The authentication banner (bytes), if any.
    """

    def __init__(
        self,
        test,
        reply=None,
        *,
        capabilities=(BASE, CANDIDATE),
        chunk_size=None,
        piece_size=None,
        subsystem=True,
        channels=True,
        ignore_close_session=False,
        banner=None,
    ):
        self.reply = reply or (lambda rpc: '<ok/>')
        self.capabilities = capabilities
        self.chunk_size = chunk_size
        self.piece_size = piece_size
        self.ignore_close_session = ignore_close_session
        self.banner = banner
        self.client_hello = None
        self.hello_received = threading.Event()
        self.rpcs = []
        self.channel = None  # of the latest session
        self.chunked = False
        self._threads = []
        test.addCleanup(self._join)  # after the server closed the transports
        key = paramiko.RSAKey(filename=KEYFILE)
        self.port = KeyServer(test, key, interface=self._interface(subsystem, channels)).port

    def _interface(self, subsystem, channels):
        fake = self

        class Interface(paramiko.ServerInterface):
            def get_banner(self):
                return fake.banner, 'en'

            def get_allowed_auths(self, username):
                return 'password'

            def check_auth_password(self, username, password):
                return paramiko.AUTH_SUCCESSFUL

            def check_channel_request(self, kind, chanid):
                if channels:
                    return paramiko.OPEN_SUCCEEDED
                return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

            def check_channel_subsystem_request(self, channel, name):
                if not subsystem or name != 'netconf':
                    return False
                thread = threading.Thread(target=fake._serve, args=(channel,))
                fake._threads.append(thread)
                thread.start()
                return True

        return Interface

    def _join(self):
        for thread in self._threads:
            thread.join(5)

    def send(self, message):
        """Sends a message (str or bytes), framed like the messages of the session."""
        if isinstance(message, str):
            message = message.encode('utf-8')
        sizes = [self.chunk_size] * (len(message) // self.chunk_size + 1) if self.chunk_size else []
        self._write(encode_message(message, self.chunked, sizes))

    def _write(self, data):
        size = self.piece_size or len(data)
        for pos in range(0, len(data), size):
            self.channel.sendall(data[pos : pos + size])

    def _serve(self, channel):
        self.channel = channel
        capabilities = ''.join(f'<capability>{c}</capability>' for c in self.capabilities)
        hello = (
            f'<hello xmlns="{NS}"><capabilities>{capabilities}</capabilities>'
            '<session-id>4711</session-id></hello>'
        )
        stream = b''

        def read(chunked):
            nonlocal stream
            while not (messages := decode_messages(stream, chunked)[0]):
                data = channel.recv(65536)
                if not data:
                    return None
                stream += data
            message, sizes = messages[0]
            stream = stream[len(encode_message(message, chunked, sizes)) :]
            return message

        try:
            self._write(hello.encode() + EOM)  # hellos are always framed like this
            self.client_hello = read(chunked=False)
            if self.client_hello is None:
                return
            self.chunked = BASE_11 in self.capabilities and BASE_11.encode() in self.client_hello
            self.hello_received.set()
            while (rpc := read(self.chunked)) is not None:
                self.rpcs.append(rpc)
                closing = operation(rpc) == 'close-session'
                if closing and self.ignore_close_session:
                    continue
                content = '<ok/>' if closing else self.reply(rpc)
                if content is CLOSE:
                    break
                if content is None:
                    continue
                if isinstance(content, str):
                    content = content.encode('utf-8')
                message_id = _message_id.search(rpc).group(1)
                self.send(
                    b'<rpc-reply xmlns="%s" message-id="%s">%s</rpc-reply>'
                    % (NS.encode(), message_id, content)
                )
                if closing:
                    break
        except (OSError, EOFError):  # paramiko raises EOFError when the client closed
            pass
        finally:
            try:
                channel.close()  # sends a message, which fails if the client closed first
            except (OSError, EOFError):
                pass


def operation(rpc):
    """Returns the name of the operation in the given RPC."""
    root = etree.fromstring(rpc.strip())
    return etree.QName(root[0]).localname


class SessionTest(unittest.TestCase):
    """Sessions with a NETCONF 1.0 server."""

    def login(self, reply=None, driver=None, timeout=1, **kwargs):
        self.server = NetconfServer(self, reply, **kwargs)
        conn = Netconf(
            timeout=timeout,
            connect_rate_limit=0,
            verify_fingerprint=False,
            preferred_authentications=['password'],
            driver=driver,
        )
        self.addCleanup(conn.close, force=True)
        conn.connect('127.0.0.1', self.server.port)
        conn.login(Account('admin', 'S3cr3t', needs_lock=False))
        return conn

    def testHello(self):
        conn = self.login()
        self.assertEqual(conn.get_server_capabilities(), [BASE, CANDIDATE])
        self.assertEqual(conn.get_session_id(), '4711')
        self.assertIn(BASE_11, conn.get_client_capabilities())
        self.assertTrue(self.server.hello_received.wait(5))
        self.assertIn(BASE_11.encode(), self.server.client_hello)
        self.assertTrue(conn.is_app_authorized())
        # The response of the login is the hello, which has no element.
        self.assertIn('<session-id>4711</session-id>', conn.response)
        self.assertIsNone(conn.get_response_element())

    def testExecute(self):
        conn = self.login(lambda rpc: '<data><system><hostname>r1</hostname></system></data>')
        conn.execute(GET_CONFIG)
        self.assertEqual([operation(rpc) for rpc in self.server.rpcs], ['get-config'])
        self.assertTrue(conn.response.startswith('<rpc-reply '), conn.response)
        self.assertNotIn(']]>]]>', conn.response)
        element = conn.get_response_element()
        self.assertEqual(element.tag, f'{{{NS}}}rpc-reply')
        self.assertEqual(element.findtext(f'.//{{{NS}}}hostname'), 'r1')

    def testFraming11(self):
        # Many small chunks, written in pieces that do not end with them.
        content = '<data><system><hostname>r1</hostname><location>rack 7</location></system></data>'
        conn = self.login(
            lambda rpc: content, capabilities=(BASE, BASE_11), chunk_size=7, piece_size=5
        )
        conn.execute(GET_CONFIG)
        self.assertTrue(self.server.chunked)
        self.assertEqual([operation(rpc) for rpc in self.server.rpcs], ['get-config'])
        self.assertNotIn('\n#', conn.response)
        self.assertTrue(conn.response.endswith(content + '</rpc-reply>'), conn.response)
        element = conn.get_response_element()
        self.assertEqual(element.findtext(f'.//{{{NS}}}location'), 'rack 7')

    def testUTF8(self):
        # NETCONF is UTF-8 (RFC 6241), whatever the encoding argument says. The reply arrives
        # in one read: ncclient's parser fails if a character spans two.
        content = '<data><location>Zürich – 3 €</location></data>'
        for capabilities in (BASE,), (BASE, BASE_11):
            with self.subTest(capabilities=capabilities):
                conn = self.login(lambda rpc: content, capabilities=capabilities)
                conn.execute('<get><filter><location>Zürich</location></filter></get>')
                self.assertIn('<location>Zürich</location>'.encode(), self.server.rpcs[0])
                self.assertTrue(conn.response.endswith(content + '</rpc-reply>'), conn.response)
                self.assertIn('<location>Zürich</location>', conn.stdout.getvalue())  # sent
                self.assertIn(content, conn.stdout.getvalue())

    def testBannerThatIsNoUTF8(self):
        # SSH banners are UTF-8, too (RFC 4252), but other bytes must not fail the login.
        conn = self.login(banner='Grüße\n'.encode('latin-1'))
        self.assertEqual(conn.get_banner(), 'Gr\ufffd\ufffde\n')

    def testNotification(self):
        conn = self.login()
        conn.execute(
            '<create-subscription xmlns="urn:ietf:params:xml:ns:netconf:notification:1.0"/>'
        )
        self.server.send(NOTIFICATION)
        conn.expect('</notification>')
        self.assertIn('<event>link down</event>', conn.response)

    def testSecondLoginKeepsTheSession(self):
        conn = self.login()
        session = conn._ncc_session
        account = Account('admin', 'S3cr3t', needs_lock=False)
        conn.login(account, app_account=Account('other', 'secret', needs_lock=False))
        self.assertIs(conn._ncc_session, session)
        conn.execute(GET_CONFIG)
        self.assertEqual(len(self.server.rpcs), 1)

    def testRPCErrors(self):
        errors = (
            '<rpc-error><error-type>application</error-type><error-tag>invalid-value</error-tag>'
            '<error-severity>error</error-severity><error-app-tag>too-big</error-app-tag>'
            '<error-path>/interfaces/interface[name="eth0"]/mtu</error-path>'
            '<error-message xml:lang="en">MTU out of range</error-message>'
            '<error-info><bad-element>mtu</bad-element></error-info></rpc-error>'
            '<rpc-error><error-type>protocol</error-type><error-tag>operation-failed</error-tag>'
            '<error-message>commit failed</error-message></rpc-error>'
        )
        conn = self.login(lambda rpc: errors)
        with self.assertRaises(RPCError) as cm:
            conn.execute('<commit/>')
        error = cm.exception
        self.assertEqual(str(error), 'error: MTU out of range')
        self.assertEqual(error.errlist[0], error)
        self.assertEqual(
            (error.type, error.tag, error.severity, error.message, error.app_tag, error.path),
            (
                'application',
                'invalid-value',
                'error',
                'MTU out of range',
                'too-big',
                '/interfaces/interface[name="eth0"]/mtu',
            ),
        )
        self.assertIn('<bad-element>mtu</bad-element>', error.info)
        self.assertEqual(etree.QName(error.element).localname, 'rpc-error')
        other = error.errlist[1]
        self.assertEqual(
            (str(other), other.severity, other.tag), ('commit failed', '', 'operation-failed')
        )
        self.assertIn('MTU out of range', conn.response)  # the full reply

    def testWarningsAreNoErrors(self):
        # Without <ok/>, like servers send warnings (RFC 6241, section 4.4).
        conn = self.login(lambda rpc: WARNING)
        conn.execute('<commit/>')
        self.assertIn('deprecated', conn.response)

    def testErrorAfterAWarning(self):
        conn = self.login(lambda rpc: WARNING + LOCK_ERROR)
        with self.assertRaises(RPCError) as cm:
            conn.execute(LOCK)
        error = cm.exception
        self.assertEqual(str(error), 'error: configuration database locked')
        self.assertEqual([e.severity for e in error.errlist], ['warning', 'error'])
        self.assertIs(error.errlist[1], error)

    def testInvalidRPCIsNotSent(self):
        conn = self.login()
        with self.assertRaises(XMLValidationError) as cm:
            conn.execute('<get-config><source><running/></get-config>')
        self.assertIn('XMLSyntaxError', str(cm.exception))
        self.assertIn('<get-config>', cm.exception.xmlstring)
        self.assertTrue(any('shifted by +1' in note for note in cm.exception.__notes__))
        with self.assertRaises(XMLValidationError) as cm:
            conn.execute('<get-config>\ud800</get-config>')  # not encodable
        cause = cm.exception.__context__
        self.assertIsInstance(cause, UnicodeEncodeError)
        self.assertEqual((cause.start, cause.end), (12, 13))  # the positions in the body
        self.assertEqual(self.server.rpcs, [])

    def testRPCBodyIsOneElement(self):
        conn = self.login()
        for body in '<get-config/><get/>', 'hello', '<get/>hello', '':
            with self.subTest(body=body):
                with self.assertRaisesRegex(XMLValidationError, 'must be one XML element') as cm:
                    conn.execute(body)
                self.assertEqual(cm.exception.xmlstring, body + '\r')
        conn.execute('\n  <get/>\n')  # whitespace is no content
        self.assertEqual([operation(rpc) for rpc in self.server.rpcs], ['get'])

    def testTimeout(self):
        conn = self.login(lambda rpc: None if operation(rpc) == 'get' else '<ok/>', timeout=0.3)
        self.assertRaises(TimeoutException, conn.execute, '<get/>')
        self.assertIsNone(conn.get_response_element())
        self.assertRaises(TimeoutException, conn.expect, 'never')

    def testSetTimeoutAfterLogin(self):
        # Each RPC waits as long as the current timeout says, also close-session.
        timeouts = []
        request = RPC._request

        def record(rpc, op):
            timeouts.append(rpc.timeout)
            return request(rpc, op)

        conn = self.login()
        with mock.patch.object(RPC, '_request', record):
            conn.set_timeout(5)
            conn.execute(GET_CONFIG)
            conn.set_timeout(7)
            conn.close()
        self.assertEqual(timeouts, [5, 7])

    def testServerClosesTheSession(self):
        conn = self.login(lambda rpc: CLOSE, timeout=0.3)
        thread = conn._ncc_session
        self.assertRaises(ConnectionClosedException, conn.execute, '<get/>')
        self.assertRaises(ConnectionClosedException, conn.expect_prompt)
        thread.join(5)  # then ncclient marks the session as closed
        self.assertRaises(ConnectionClosedException, conn.execute, '<get/>')
        conn.close()  # the logout fails silently
        self.assertFalse(conn.connected)

    def testCloseSession(self):
        sent = []
        conn = self.login()
        conn.data_sent_event.connect(sent.append)
        conn.close()
        self.assertEqual([operation(rpc) for rpc in self.server.rpcs], ['close-session'])
        self.assertIn('close-session/>', ''.join(sent))  # pretty-printed
        self.assertFalse(conn.connected)

    def testCloseEndsTheIOThread(self):
        # ncclient closes the session itself after the reply to close-session.
        for ignore_close_session, force in (False, False), (True, False), (False, True):
            with self.subTest(ignore_close_session=ignore_close_session, force=force):
                conn = self.login(timeout=0.3, ignore_close_session=ignore_close_session)
                thread = conn._ncc_session
                conn.close(force=force)
                self.assertFalse(thread.is_alive())

    def testSubsystemRefused(self):
        for options in {'subsystem': False}, {'channels': False}:
            with self.assertRaisesRegex(LoginFailure, 'any subsystem: netconf'):
                self.login(**options)

    def testHugeTree(self):
        depth = 300  # lxml refuses documents nested deeper than 256 levels without huge_tree
        content = '<data>' + '<a>' * depth + '</a>' * depth + '</data>'
        server = NetconfServer(self, lambda rpc: content)
        conn = Netconf(
            timeout=1,
            connect_rate_limit=0,
            verify_fingerprint=False,
            preferred_authentications=['password'],
        )
        self.addCleanup(conn.close, force=True)
        self.assertFalse(conn.huge_tree)
        conn.huge_tree = True
        conn.connect('127.0.0.1', server.port)
        conn.login(Account('admin', 'S3cr3t', needs_lock=False))
        self.assertTrue(conn._ncc_manager.huge_tree)
        conn.execute(GET_CONFIG)
        self.assertEqual(len(conn.get_response_element().xpath('//*[local-name()="a"]')), depth)
        conn.huge_tree = False
        self.assertFalse(conn._ncc_manager.huge_tree)

    def testDeviceHandlerThatTransformsTheReply(self):
        # The Junos device handler of ncclient returns the reply as an NCElement.
        driver = drivers.Driver('junos-netconf')
        driver.netconf_device_params = {'name': 'junos'}
        replies = iter(['<data><version>23.4R1</version></data>', LOCK_ERROR])
        conn = self.login(lambda rpc: next(replies), driver=driver)
        conn.execute(GET_CONFIG)
        self.assertIsInstance(conn._ncc_response, NCElement)
        self.assertEqual(conn.get_response_element().findtext('.//version'), '23.4R1')
        with self.assertRaisesRegex(RPCError, 'error: configuration database locked'):
            conn.execute(LOCK)


NOTIFICATION = (
    '<notification xmlns="urn:ietf:params:xml:ns:netconf:notification:1.0">'
    '<eventTime>2026-11-10T12:00:00Z</eventTime><event>link down</event></notification>'
)
LOCK_ERROR = (
    '<rpc-error><error-type>protocol</error-type><error-tag>lock-denied</error-tag>'
    '<error-severity>error</error-severity>'
    '<error-message>configuration database locked</error-message></rpc-error>'
)
WARNING = (
    '<rpc-error><error-type>application</error-type><error-tag>operation-failed</error-tag>'
    '<error-severity>warning</error-severity><error-message>deprecated</error-message>'
    '</rpc-error>'
)


class RPCErrorTest(unittest.TestCase):
    def testOnlyWarnings(self):
        # The raised error is the first with the severity error, else the first one.
        content = WARNING + WARNING.replace('deprecated', 'slow')
        reply = RPCReply(f'<rpc-reply xmlns="{NS}" message-id="1">{content}</rpc-reply>')
        error = RPCError._from_ncclient(reply.errors)
        self.assertEqual(error.message, 'deprecated')
        self.assertEqual([e.message for e in error.errlist], ['deprecated', 'slow'])


class ReplayedSessionTest(unittest.TestCase):
    """The NETCONF 1.1 session of netopeer2, replayed."""

    def setUp(self):
        server = ReplayServer(Recording(RECORDING))
        server.__enter__()
        self.addCleanup(server.close)
        self.stdout = io.StringIO()
        self.conn = Netconf(
            timeout=2,
            connect_rate_limit=0,
            verify_fingerprint=False,
            preferred_authentications=['password'],
            stdout=self.stdout,
        )
        self.addCleanup(self.conn.close, force=True)
        self.conn.connect('127.0.0.1', server.port)
        self.conn.login(Account('admin', 'S3cr3t', needs_lock=False))
        self.server = server

    def testHello(self):
        capabilities = self.conn.get_server_capabilities()
        self.assertIn(BASE_11, capabilities)
        self.assertIn('urn:ietf:params:netconf:capability:writable-running:1.0', capabilities)
        self.assertEqual(self.conn.get_session_id(), '1')
        self.assertEqual(self.conn.guess_os(), 'unknown')

    def testGetConfigAndFilter(self):
        self.conn.execute(GET_CONFIG)
        self.assertNotIn('\n##\n', self.conn.response)  # the chunks are reassembled
        element = self.conn.get_response_element()
        keystore = '{urn:ietf:params:xml:ns:yang:ietf-keystore}keystore'
        self.assertIsNotNone(element.find(f'{{{NS}}}data/{keystore}'))
        self.assertEqual(self.conn.get_response(), self.conn.response.strip())

        self.conn.execute(FILTER)
        element = self.conn.get_response_element()
        monitoring = '{urn:ietf:params:xml:ns:yang:ietf-netconf-monitoring}'
        capabilities = element.findall(f'.//{monitoring}capability')
        self.assertIn(BASE_11, [capability.text for capability in capabilities])

    def testLockedTwice(self):
        self.conn.execute(GET_CONFIG)
        self.conn.execute(FILTER)
        self.conn.execute(LOCK)
        with self.assertRaises(RPCError) as cm:
            self.conn.execute(LOCK)
        messages = [error.message for error in cm.exception.errlist]
        self.assertEqual(messages, ['Requested resource already locked', 'User callback failed.'])
        self.assertEqual({error.tag for error in cm.exception.errlist}, {'operation-failed'})

    def testCloseSession(self):
        self.conn.close()
        self.assertIn('close-session/>', self.stdout.getvalue())
        self.assertEqual(self.server.errors, [])
