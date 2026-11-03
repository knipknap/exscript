"""Tests for the parts of the NETCONF adapter that need no server."""

import inspect
import threading
import unittest

import ncclient.operations.rpc
import ncclient.transport.session
from ncclient.manager import make_device_handler
from ncclient.operations.rpc import RPC, RPCReply
from ncclient.transport.session import HelloHandler
from ncclient.transport.ssh import SSHSession
from ncclient.xml_ import NCElement, new_ele

from Exscript.protocols import netconf
from Exscript.protocols.netconf import Netconf

BASE = 'urn:ietf:params:netconf:base:1.0'


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
        self.assertIs(ncclient.operations.rpc.to_xml, netconf._to_xml)
        self.assertIs(ncclient.transport.session.to_xml, netconf._to_xml)
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
