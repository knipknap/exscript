The Python API
==============

Overview
--------

*Exscript* provides simple, yet powerful Python APIs. There are two
ways in which *Exscript* APIs may be used:

#. “*Exscript* .protocols” is a simple replacement for Python’s built-in
   telnetlib.

#. “*Exscript* .Queue” is a powerful, multi-threaded environment for
   automating more complex tasks. It comes with features such as
   logging, user account management, and error handling that make things
   a lot easier. This is the recommended way of using Exscript.

*Exscript* .protocols
---------------------

The telnetlib module shipped with Python is incomplete, poorly
implemented, and does not feature a generic API. To make it easy to
access hosts via Telnet and SSH using the exact same API, *Exscript*
.protocols provides a clean and simple replacement. *Exscript*
supports the following protocols at this time:

#. *Telnet* is a Telnet adapter.

#. *SSH* is an adapter for SSH version 1 and version 2.

#. *Dummy* is a virtual pseudo device that may be used for testing.

The following example shows how to connect to a host using Telnet:

::

    from Exscript.protocols import Telnet

    conn = Telnet()
    conn.connect("127.0.0.1") # The default port is 21
    conn.authenticate("myuser", "mypassword")
    conn.execute("ls -l")
    conn.send("exit\r")
    conn.close()

The example will execute the “ls -l” command on the remote host, and
waits until the remote host has responded with a prompt. Once the prompt
was retrieved, the function returns and “conn.send(“exit”)” is reached.
Unlike *execute()*, the *send()* method returns immediately without
waiting for a response from the remote host. This is necessary here,
because the remote host does not normally respond to the “exit” command;
it just closes the connection.

The above code also works with SSH - just replace “Telnet” with SSH:

::

    from Exscript.protocols import SSH
    conn = SSH()
    ...

To fetch the response of a remote host, the following code may be used:

::

    ...
    conn.execute("ls -l")
    print "The host said:", repr(conn.response)

Emulating A Remote Device
~~~~~~~~~~~~~~~~~~~~~~~~~

*Exscript* also provides a dummy protocol adapter for testing
purposes. It emulates a remote host and may be used in place of the
Telnet and SSH adapters:

::

    from Exscript.protocols import Dummy
    conn = Dummy()
    ...

In order to define the behavior of the dummy, you may define it by
providing a Python file that maps commands to responses. E.g.:

::

    def echo(command):
        return command.split(' ', 1)[1]

    commands = (
    ('ls -l', """
    -rw-r--r-- 1 sab nmc 1906 Oct  5 11:18 Makefile
    -rw-r--r-- 1 sab nmc 1906 Oct  5 11:18 myfile
    """),

    (r'echo [\r\n]+', echo)
    )

Note that the command name is a regular expression, and the response may
be either a string or a function.

*Exscript* .Queue
-----------------

The more powerful and recommended way of using Exscript is by using
*Exscript* .Queue. Consider the following simple example:

This code reads a list of hostnames from “hostlist.txt”, automatically
logs into each of the hosts, and executes the “do_something” once for
each of the hosts.

The “quickstart()” function is a shortcut that you can use in most
cases. However, there are some more advanced features that you can use.
For example, Exscript can generate a report for all of the executed
tasks:

*Exscript* provides additional methods, and also offers
protocol-specific options. For a complete list of supported methods
please refer to our API documentation.

The Standard Library
====================

.. automodule:: Exscript.stdlib
