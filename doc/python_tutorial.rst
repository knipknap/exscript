Python Tutorial
===============

Introduction
------------

This is a step by step introduction to using Exscript in
`Python <http://www.python.org/>`_.

We'll assume that Exscript is already installed. You can confirm that
your installation works by typing ``exscript --version`` into a
terminal; if this prints the version number, your installation is
complete.

We will also assume that you have at least a little bit of programming
experience, though most of the examples should be pretty simple.

Exscript also has extensive :doc:`API documentation <modules>`, which may
be used as a reference throughout this tutorial.

Getting started
---------------

As a first simple test, let's try to connect to a network device via
SSH2, and execute the ``uname -a`` command on it.

Create a file named ``start.py`` with the following content::

    from Exscript.util.interact import read_login
    from Exscript.protocols import SSH2

    account = read_login()    # Prompt the user for his name and password
    conn = SSH2()             # We choose to use SSH2
    conn.connect('localhost') # Open the SSH connection
    conn.login(account)       # Authenticate on the remote host
    conn.execute('uname -a')  # Execute the "uname -a" command
    conn.send('exit\r')       # Send the "exit" command
    conn.close()              # Wait for the connection to close

Awesome fact: Just replace ``SSH2`` by ``Telnet`` and it should
still work with Telnet devices.

As you can see, we prompt the user for a username and a password, and
connect to ``localhost`` using the entered login details. Once logged
in, we execute ``uname -a``, log out, and make sure to wait until the
remote host has closed the connection.

You can see one important difference: We used ``conn.execute`` to run
``uname -a``, but we used ``conn.send`` to execute the ``exit`` command.
The reason is that *``conn.execute`` waits until the server has
acknowledged that the command has completed*, while ``conn.send`` does
not. Since the server won't acknowledge the ``exit`` command (instead,
it just closes the connection), using ``conn.execute`` would lead to an
error.

Making it easier
----------------

While the above serves as a good introduction on how to use
:mod:`Exscript.protocols`, it has a few drawbacks:

#. It only works for SSH2 or for Telnet, but not for both.
#. It contains a lot of unneeded code.
#. You can't use the script to connect to multiple hosts.

Let's solve drawbacks 1. and 2. first. Here is a shortened version of
the above script::

    from Exscript.util.start import quickstart

    def do_something(job, host, conn):
        conn.execute('uname -a')

    quickstart('ssh://localhost', do_something)

As you can see, we made two major changes:

#. We moved the code that executes ``uname -a`` into a function named
   ``do_something``. (Note: We could have picked any other name for the
   function.)
#. We imported and used the :func:`Exscript.util.start.quickstart` function.

:func:`Exscript.util.start.quickstart` does the following:

#. It prompts the user for a username and a password.
#. It connects to the specified host, using the specified protocol.
#. It logs in using the given login details.
#. It calls our ``do_something()`` function.
#. When ``do_something()`` completes, it closes the connection.

Running a script on multiple hosts
----------------------------------

In practice, you may want to run this script on multiple hosts, and
optimally at the same time, in parallel. Using the
:func:`Exscript.util.start.quickstart`
function, this is now really easy::

    from Exscript.util.start import quickstart

    def do_something(job, host, conn):
        conn.execute('uname -a')

    hosts = ['ssh://localhost', 'telnet://anotherhost']
    quickstart(hosts, do_something, max_threads=2)

We only changed the last lines of the script:

#. We pass in two hosts, ``localhost`` and ``anotherhost``. Note that
   ``localhost`` uses SSH, and ``anotherhost`` speaks Telnet.
#. We added the ``max_threads=2`` argument. This tells Exscript to
   open two network connections in parallel.

If you run this script, it will again ask for the login details, and run
``do_something()`` for both hosts in parallel.

Note that the login details are only asked once and used on both hosts -
this may or may not be what you want. For instructions one using
different login mechanisms please refer to the section on accounts
later.

Loading hosts from a text file
------------------------------

If you do not wish to hard code the host names into the script, you may
also list them in a text file and load it using
:func:`Exscript.util.file.get_hosts_from_file` as follows::

    from Exscript.util.start import start
    from Exscript.util.file import get_hosts_from_file

    def do_something(job, host, conn):
        conn.execute('uname -a')

    hosts = get_hosts_from_file('myhosts.txt')
    start(hosts, do_something, max_threads=2)

Reading login information
-------------------------

Depending on how you would like to provide the login information, there
are a few options. The first is by hard coding it into the hostname::

    hosts = ['ssh://localhost', 'telnet://myuser:mypassword@anotherhost']
    quickstart(hosts, do_something, max_threads=2)

In this case, ``quickstart`` still prompts the user for his login
details, but the entered information is only used on hosts that do not
have a user/password combination included in the hostname.

If you do not wish to hard code the login details into the hostname, you
can also use the Exscript.Host object as shown in the following script::

    from Exscript import Host, Account
    …
    account1 = Account('myuser', 'mypassword')
    host1 = Host('ssh://localhost')
    host1.set_account(account1)

    account2 = Account('myuser2', 'mypassword2')
    host2 = Host('ssh://otherhost')
    host2.set_account(account2)

    quickstart([host1 , host2], do_something, max_threads=2)

This script still has the problem that it prompts the user for login
details, even though the details are already known. By using
:func:`Exscript.util.start.start` instead of
:func:`Exscript.util.start.quickstart`, you can avoid the prompt,
and optionally pass in a pre-loaded list of accounts as seen in the
following code::

    from Exscript.util.start import start
    from Exscript.util.file import get_hosts_from_file

    def do_something(job, host, conn):
        conn.execute('uname -a')

    accounts = [] # No account needed.
    hosts = get_hosts_from_file('myhosts.txt')
    start(accounts, hosts, do_something, max_threads=2)

Instead of passing in no account at all, you may also create one in the
script::

    from Exscript import Account
    …
    accounts = [Account('myuser', 'mypassword')]
    …

Or you may load it from an external file::

    from Exscript.util.file import get_accounts_from_file
    …
    accounts = get_accounts_from_file('accounts.cfg')
    …

Note that ``accounts.cfg`` is a config file with a defined syntax as
seen in the API documentation for
:func:`Exscript.util.file.get_accounts_from_file`.

Logging
-------

Exscript has built-in support for logging. In a simple case, just pass
the ``stdout`` and ``stderr`` parameters for log and errors to
``start()`` or ``quickstart()`` and you are done::

    with open('log.txt','w+') as fp:
        start(accounts, hosts, do_something, stdout=fp)

Exscript creates one logfile per device. In the case that an error
happened on the remote device, it creates an additional file that
contains the error (including Python's traceback).

Interacting with a device
-------------------------

So far we only fired and forgot a command on a device, there was no true
interaction. But Exscript does a lot to make interaction with a device
easier. The first notable tool is :mod:`Exscript.util.match` - a module
that builds on top of Python's regular expression support. Let's look at
an example::

    from Exscript.util.start import quickstart
    from Exscript.util.match import first_match

    def do_something(job, host, conn):
        conn.execute('uname -a')
        print "The response was", repr(conn.response)
        os, hostname = first_match(conn, r'^(\S+)\s+(\S+)')
        print "The hostname is:", hostname
        print "Operating system:", os

    quickstart('ssh://localhost', do_something)

The experienced programmer will probably wonder what happens when
:func:`Exscript.util.match.first_match` does not find a match. The
answer is: It will return a tuple ``None, None``.
In other words, no matter what happens, the one liner can not fail,
because :func:`Exscript.util.match.first_match` always returns a tuple
containing the same number of elements as there are groups (bracket
expressions) in the regular expression. This is more terse than the
following typical regular idiom::

    match = re.match(r'^(\S+)\s+(\S+)', conn.response)
    if match:
        print match.group(1)

Similarly, the following use of :func:`Exscript.util.match.any_match`
can never fail::

    from Exscript.util.start import quickstart
    from Exscript.util.match import any_match

    def do_something(job, host, conn):
        conn.execute('ls -l')
        for permissions, filename in any_match(conn, r'^(\S+).*\s+(\S+)$'):
            print "The filename is:", filename
            print "The permissions are:", permissions

    quickstart('ssh://localhost', do_something)

:func:`Exscript.util.match.any_match` is designed such that it always
returns a list, where each item contains a tuple of the same size. So
there is no need to worry about checking the return value first.

Advanced queueing and reporting
-------------------------------

:class:`Exscript.Queue` is a powerful, multi-threaded environment for
automating more complex tasks. It comes with features such as
logging, user account management, and error handling that make things
a lot easier. The above functions :func:`Exscript.util.start.start` and
:func:`Exscript.util.start.quickstart` are just convenience wrappers
around this queue.

In some cases, you may want to use the :class:`Exscript.Queue` directly.
Here is a complete example that also implements reporting:

.. literalinclude:: ../demos/report/report.py

Emulating a remote device
-------------------------

Exscript also provides a dummy protocol adapter for testing
purposes. It emulates a remote host and may be used in place of the
Telnet and SSH adapters::

    from Exscript.protocols import Dummy
    conn = Dummy()
    ...

In order to define the behavior of the dummy, you may define it by
providing a Python file that maps commands to responses. E.g.::

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
