import logging
import socket
import unittest
from unittest import mock

from hypothesis import given
from hypothesis import strategies as st

from Exscript.protocols import telnetlib
from Exscript.protocols.telnetlib import DO, DONT, IAC, NAWS, SB, SE, TTYPE, WILL, WONT, Telnet

from .listener import listen

ECHO, SGA, BINARY, NOP = 1, 3, 0, 241


class FakeSock:
    """Returns the given chunks from recv(), then EOF, and records the sent data."""

    def __init__(self, chunks):
        self.chunks = list(chunks)
        self.sent = []
        self.closed = False

    def recv(self, size):
        return self.chunks.pop(0) if self.chunks else b''

    def sendall(self, data):
        self.sent.append(bytes(data))

    def settimeout(self, timeout):
        pass

    def close(self):
        self.closed = True


def process(chunks, encoding='latin-1'):
    """Returns the text passed to the callback and the sent bytes."""
    tn = Telnet(encoding=encoding, termtype='vt100', termsize=(24, 80))
    tn.sock = FakeSock(chunks)
    received = []
    tn.data_callback = received.append
    while tn.receive(None):
        pass
    return ''.join(received), b''.join(tn.sock.sent)


def iac(*codes):
    return bytes([IAC, *codes])


segments = st.one_of(
    st.binary(max_size=30),
    st.sampled_from([iac(IAC), iac(NOP), iac(0), iac(SE), iac(SB, TTYPE, 1) + iac(SE)]),
    st.builds(iac, st.sampled_from([DO, DONT, WILL, WONT]), st.integers(0, 255)),
    st.builds(
        lambda data: iac(SB) + data.replace(b'\xff', b'\xff\xff') + iac(SE), st.binary(max_size=8)
    ),
)


class telnetlibTest(unittest.TestCase):
    CORRELATE = telnetlib

    def testData(self):
        stream = b'a\x00b\x11c' + iac(IAC) + b'd' + iac(NOP) + iac(0) + b'e'
        text, sent = process([stream])
        self.assertEqual(text, 'ab\x11c\xffde')  # NUL is removed, XON is kept
        self.assertEqual(sent, b'')

    def testNegotiation(self):
        replies = {
            iac(DO, TTYPE): iac(WILL, TTYPE),
            iac(DO, NAWS): iac(WILL, NAWS) + iac(SB, NAWS, 0, 80, 0, 24) + iac(SE),
            iac(DO, SGA): iac(WONT, SGA),
            iac(DO, BINARY): iac(WONT, BINARY),
            iac(DONT, NAWS): iac(WONT, NAWS),
            iac(DONT, BINARY): iac(WONT, BINARY),
            iac(WILL, ECHO): iac(DO, ECHO),
            iac(WONT, ECHO): iac(DO, ECHO),
            iac(WILL, SGA): iac(DONT, SGA),
            iac(WONT, BINARY): iac(DONT, BINARY),
            iac(SB, TTYPE, 1) + iac(SE): iac(SB, TTYPE, 0) + b'vt100' + iac(SE),
            iac(SB, TTYPE, 0) + b'xterm' + iac(SE): b'',
            iac(SB, BINARY, 1) + iac(SE): b'',
        }
        for stream, reply in replies.items():
            self.assertEqual(process([b'x' + stream + b'y']), ('xy', reply), stream)

    def testSubnegotiation(self):
        # An escaped IAC inside the subnegotiation does not end it.
        stream = iac(SB, NAWS, IAC, IAC, SE) + b'data' + iac(SE) + b'x'
        self.assertEqual(process([stream])[0], 'x')
        # An unterminated subnegotiation ends at the next command.
        stream = iac(SB, TTYPE, 1) + iac(DO, TTYPE) + b'x'
        self.assertEqual(process([stream]), ('x', iac(WILL, TTYPE)))

    def testIncompleteCommandAtEof(self):
        for stream in iac(), iac(DO), iac(SB, TTYPE, 1), iac(SB, TTYPE, 1, IAC):
            self.assertEqual(process([b'x' + stream]), ('x', b''))

    def testEveryReadSplit(self):
        stream = (
            b'a' + iac(DO, NAWS) + iac(SB, TTYPE, 1) + iac(SE) + iac(IAC) + iac(WILL, ECHO) + b'z'
        )
        expected = process([stream])
        for cut in range(1, len(stream)):
            self.assertEqual(process([stream[:cut], stream[cut:]]), expected, cut)

    @given(st.lists(segments, max_size=20), st.lists(st.integers(1, 60), max_size=8))
    def testSplitDoesNotMatter(self, parts, sizes):
        stream = b''.join(parts)
        chunks, pos = [], 0
        for size in sizes:
            chunks.append(stream[pos : pos + size])
            pos += size
        chunks.append(stream[pos:])
        self.assertEqual(process([chunk for chunk in chunks if chunk]), process([stream]))

    def testMultibyteCharacterSplit(self):
        stream = 'Grüße 20 €'.encode()
        for cut in range(1, len(stream)):
            text, _ = process([stream[:cut], stream[cut:]], encoding='utf-8')
            self.assertEqual(text, 'Grüße 20 €', cut)

    def testReceive(self):
        local, remote = socket.socketpair()
        self.addCleanup(remote.close)
        tn = Telnet(connect_timeout=7)
        tn.sock = local
        received = []
        tn.data_callback = received.append
        self.assertIsNone(tn.receive(0))  # no data yet
        self.assertIsNone(tn.receive(0.05))
        remote.sendall(b'hello')
        self.assertTrue(tn.receive(5))
        self.assertEqual(received, ['hello'])
        self.assertEqual(local.gettimeout(), 7)  # restored for sendall()
        remote.close()
        self.assertFalse(tn.receive(5))
        self.assertFalse(tn.receive(5))
        tn.close()

    def testWrite(self):
        tn = Telnet()
        tn.sock = FakeSock([])
        tn.set_debuglevel(1)
        with self.assertNoLogs('Exscript.protocols.telnetlib', logging.DEBUG):  # may be a password
            tn.write('sécret\xff\r')
        tn.write(b'\xff')
        self.assertEqual(tn.sock.sent, [b's\xe9cret\xff\xff\r', b'\xff\xff'])

    def testSetWindowSize(self):
        tn = Telnet()
        tn.sock = FakeSock([])
        tn.set_window_size(50, 120)
        self.assertEqual(tn.sock.sent, [])  # the server did not ask for it yet
        tn.can_naws = True
        tn.set_window_size(1, 255)
        self.assertEqual(tn.sock.sent, [iac(SB, NAWS, 0, IAC, IAC, 0, 1) + iac(SE)])

    def testOpen(self):
        for family, address in (socket.AF_INET, '127.0.0.1'), (socket.AF_INET6, '::1'):
            try:
                listener = listen(address, family)
            except OSError:
                continue  # no IPv6 on this host
            with listener:
                tn = Telnet(address, listener.getsockname()[1], connect_timeout=5)
                tn.close()
                self.assertTrue(tn.eof)
        # Bound but not listening: refused everywhere, also by WSL's consomme networking, which accepts
        # connections to closed ports and closes them right away.
        with socket.socket() as bound:
            bound.bind(('127.0.0.1', 0))
            port = bound.getsockname()[1]
            with self.assertRaisesRegex(OSError, f'=> telnet://127.0.0.1:{port}'):
                Telnet('127.0.0.1', port, connect_timeout=5)

    def testOpenErrorNamesTheUrl(self):
        error = ConnectionRefusedError(111, 'Connection refused')
        with (
            mock.patch('socket.create_connection', side_effect=error),
            self.assertRaisesRegex(OSError, 'Connection refused => telnet://router1:23') as cm,
        ):
            Telnet('router1', connect_timeout=5)
        self.assertIs(cm.exception.__cause__, error)

    def testCloseTwice(self):
        local, remote = socket.socketpair()
        self.addCleanup(remote.close)
        tn = Telnet()
        tn.sock = local
        tn.close()
        tn.close()
        self.assertTrue(tn.eof)
        self.assertIsNone(tn.sock)
        self.assertEqual(local.fileno(), -1)
        self.assertFalse(tn.receive(1))

    def testCloseWhileReceiving(self):
        # Another thread closes the connection while recv() waits, and recv() still returns data.
        tn = Telnet()
        tn.sock = sock = FakeSock([b'late', b'more'])
        recv = sock.recv

        def recv_and_close(size):
            tn.close()
            return recv(size)

        sock.recv = recv_and_close
        received = []
        tn.data_callback = received.append
        self.assertFalse(tn.receive(None))
        self.assertTrue(tn.eof)
        self.assertTrue(sock.closed)
        self.assertFalse(tn.receive(None))  # the socket is None
        self.assertEqual(received, ['late'])

        # In close() in another thread, after it removed the socket, before it set eof.
        tn.eof = False
        self.assertFalse(tn.receive(None))
        self.assertEqual(received, ['late'])

    def testNawsWithoutSize(self):
        # The size is sent once it is known.
        tn = Telnet(termsize=None)
        tn.sock = FakeSock([iac(DO, NAWS)])
        while tn.receive(None):
            pass
        self.assertEqual(tn.sock.sent, [iac(WILL, NAWS)])
        tn.set_window_size(24, 80)
        self.assertEqual(tn.sock.sent[-1], iac(SB, NAWS, 0, 80, 0, 24) + iac(SE))
