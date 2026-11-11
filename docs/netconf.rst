NETCONF
=======

The :class:`~Exscript.protocols.Netconf` adapter speaks NETCONF over SSH
(:rfc:`6241`, :rfc:`6242`). It is based on `ncclient
<https://github.com/ncclient/ncclient>`_, which is installed with
Exscript. You send RPCs as XML text, and get the replies as text or as
`lxml <https://lxml.de>`_ elements.

Connecting
----------

``Netconf`` is an SSH adapter, so it takes the same arguments as
:class:`~Exscript.protocols.SSH2`, and checks host keys the same way
(:doc:`security`). The default port is 830::

    from Exscript import Account
    from Exscript.protocols import Netconf

    conn = Netconf()
    conn.connect('router1')
    conn.login(Account('admin', 'secret'))
    print(conn.get_server_capabilities())

In host lists and with :func:`Exscript.util.start.start`, use the scheme
``netconf://``, for example ``netconf://router1``.

``login()`` authenticates with SSH and exchanges the ``<hello>`` messages;
there is no login prompt. ``get_server_capabilities()``,
``get_client_capabilities()`` and ``get_session_id()`` return what was
exchanged.

NETCONF messages are UTF-8 (:rfc:`6241`), and so are SSH banners
(:rfc:`4252`), so ``Netconf`` always uses UTF-8; the ``encoding`` argument
has no effect.

Sending RPCs
------------

``execute()`` sends the content of an ``<rpc>`` element and waits for the
reply; Exscript adds the ``<rpc>`` element with its ``message-id``. It
raises :class:`~Exscript.util.xml.XMLValidationError` before sending if
the content is not well-formed XML, or not one XML element::

    conn.execute('<get-config><source><running/></source></get-config>')
    print(conn.get_response())  # the <rpc-reply> as text

    reply = conn.get_response_element()  # the <rpc-reply> as lxml element
    ns = {'ks': 'urn:ietf:params:xml:ns:yang:ietf-keystore'}
    for name in reply.xpath('//ks:asymmetric-key/ks:name/text()', namespaces=ns):
        print(name)

Filters work as with any NETCONF client::

    conn.execute('''
        <get>
          <filter type="subtree">
            <netconf-state xmlns="urn:ietf:params:xml:ns:yang:ietf-netconf-monitoring">
              <capabilities/>
            </netconf-state>
          </filter>
        </get>''')

``close()`` sends ``<close-session/>`` and closes the connection.

Messages and notifications
--------------------------

``response`` and the patterns of ``expect()`` and ``waitfor()`` see the
messages of the session, decoded and without the framing of :rfc:`6242`;
each message is followed by ``]]>]]>``, also with NETCONF 1.1. To wait for
a notification after ``<create-subscription/>``::

    conn.execute('<create-subscription '
                 'xmlns="urn:ietf:params:xml:ns:netconf:notification:1.0"/>')
    conn.expect('</notification>')
    print(conn.response)

The logs, the standard output and ``data_received_event`` show the data
as it was received, with the chunk headers of NETCONF 1.1;
``Netconf.reassemble_chunks()`` removes them.

Errors
------

If the reply contains an ``<rpc-error>`` with the severity ``error``,
``execute()`` raises :class:`~Exscript.protocols.exception.RPCError`.
Its attributes hold the first error with the severity ``error``, and
``errlist`` holds all errors of the reply, warnings too, in their order.
Replies with only warnings do not raise::

    from Exscript.protocols.exception import RPCError

    conn.execute('<lock><target><running/></target></lock>')
    try:
        conn.execute('<lock><target><running/></target></lock>')
    except RPCError as error:
        print(error.tag, error.message)  # operation-failed Requested resource already locked
        for e in error.errlist:
            print(e.type, e.tag, e.severity, e.path, e.message)
    conn.execute('<unlock><target><running/></target></unlock>')

``RPCError`` is an
:class:`~Exscript.protocols.exception.InvalidCommandException`, so code
that handles failed commands of any protocol also handles it.

Large replies
-------------

lxml limits the size and depth of the XML documents that it parses. For
replies beyond these limits, for example the full configuration of a large
device, set ``conn.huge_tree = True``. This also removes the protection
against documents that are built to exhaust the memory, so enable it only
for devices that you trust.

Drivers
-------

Exscript recognizes IOS XR, Junos and NX-OS devices by the capabilities in
their ``<hello>`` (:doc:`drivers`). The driver provides the patterns that detect
the end of a reply and errors in it, and the ncclient device handler: its
``netconf_device_params`` attribute is passed to ncclient's
``make_device_handler()``. The built-in drivers use ncclient's default
handler; for NX-OS, ncclient's ``nexus`` handler would replace the base
capability of RFC 6241 in the ``<hello>`` of the client with the one of the
old XML agent. Because the device handler is chosen when the session starts,
before the capabilities are known, pass a driver that sets
``netconf_device_params`` with ``driver=``.

Interactive sessions
--------------------

``interact()`` does not work with NETCONF. For an interactive session,
use OpenSSH::

    ssh -s -p 830 router1 netconf
