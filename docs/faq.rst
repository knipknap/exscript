Frequently Asked Questions
==========================

Why does ``send()`` return nothing?
-----------------------------------

``send()`` only sends the data; it does not wait for an answer. To run a
command and read its output, use ``execute()``, which sends the command,
waits for the prompt and keeps the output in ``conn.response``::

    conn.execute('show version')
    print(conn.response)

To wait for something other than the prompt, follow ``send()`` with
``expect()``, which waits for one or more regular expressions::

    conn.send('reload\r')
    conn.expect(r'\[confirm\]')
    conn.send('\r')

How do I answer a question of the host, such as the password of ``sudo``?
--------------------------------------------------------------------------

Send the command, wait for the question with ``expect()``, answer it, and
wait for the prompt::

    conn.send('sudo -k systemctl restart sshd\r')
    conn.expect(r'[Pp]assword.*:\s*$')
    conn.send(account.get_password() + '\r')
    conn.expect_prompt()

``sudo -k`` asks for the password even if sudo remembers an earlier one,
so the question always comes. If the host shows no prompt that Exscript
recognizes, set one with ``set_prompt()`` (see :doc:`trouble`).

Python removed ``telnetlib``. What do I use instead?
----------------------------------------------------

:class:`Exscript.protocols.Telnet` connects to any Telnet host and has the
same functions as the other protocol adapters, e.g. ``expect()``,
``waitfor()`` and ``execute()``::

    from Exscript import Account
    from Exscript.protocols import Telnet

    conn = Telnet()
    conn.connect('router1')
    conn.login(Account('admin', 'secret'))
    conn.execute('show version')
    conn.close()

``Exscript.protocols.telnetlib`` is internal. For a drop-in replacement of
the module that Python 3.13 removed, use the package
`standard-telnetlib <https://pypi.org/project/standard-telnetlib/>`_.
