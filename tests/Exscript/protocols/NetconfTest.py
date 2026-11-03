"""Tests for the parts of the NETCONF adapter that need no server."""

import unittest

from Exscript.protocols.netconf import Netconf


class ReassembleChunksTest(unittest.TestCase):
    def testChunks(self):
        # The second chunk contains what looks like a chunk header.
        self.assertEqual(Netconf.reassemble_chunks('\n#5\n<ok/>\n#3\n\n#1\n##\n'), '<ok/>\n#1')

    def testWithoutChunks(self):
        self.assertEqual(Netconf.reassemble_chunks('<rpc-reply/>'), '<rpc-reply/>')

    def testTrailingBytes(self):
        self.assertRaises(ValueError, Netconf.reassemble_chunks, '\n#2\nok\n##\nx')

    def testManyChunks(self):
        chunk = 'x' * 4096
        framed = ''.join('\n#4096\n' + chunk for _ in range(1024)) + '\n##\n'
        self.assertEqual(Netconf.reassemble_chunks(framed), chunk * 1024)
