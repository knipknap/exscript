CLI Tutorial
============

Introduction
------------

With the *exscript* command line tool, you can quickly automate a
conversation with a device over Telnet or SSH.

This is a step by step introduction to using the Exscript command line
tool.

We'll assume that Exscript is already installed. You can confirm that
your installation works by typing ``exscript --version`` into a
terminal; if this prints the version number, your installation is
complete.

Getting started
---------------

As a first simple test, let's try to connect to a Linux/Unix machine
via SSH2, and execute the ``uname -a`` command on it.

Create a file named ``test.exscript`` with the following content::

    uname -a

To run this Exscript template, just start Exscript using the following
command::

    exscript test.exscript ssh://localhost

Awesome fact: Just replace ``ssh://`` by ``telnet://`` and it should
still work with Telnet devices.

.. hint::
   The example assumes that ``localhost`` is a Unix server where
   SSH is running. You may of course change this to either an ip
   address (such as ``ssh://192.168.0.1``), or any other hostname.

Exscript will prompt you for a username and a password, and connect to
``localhost`` using the entered login details. Once logged in, it
executes ``uname -a``, waits for a prompt, and closes the connection.

Running a script on multiple hosts
----------------------------------

In practice, you may want to run this script on multiple hosts, and
optimally at the same time, in parallel. Using the ``-c`` option, you
tell Exscript to open multiple connections at the same time::

    exscript -c 2 test.exscript ssh://localhost ssh://otherhost

``-c 2`` tells Exscript to open two connections in parallel. So if you
run this script, Exscript will again ask for the login details, and run
``uname -a`` for both hosts in parallel.

Note that the login details are only asked once and used on both hosts -
this may or may not be what you want. The following section explains
some of the details of using different login accounts.

Reading login information
-------------------------

Depending on how you would like to provide the login information, there
are a few options. The first is by including it in the hostname::

    exscript -c 2 test.exscript ssh://localhost
    ssh://user:password@otherhost

In this case, Exscript still prompts the user for his login details,
but the entered information is only used on hosts that do not have a
user/password combination included in the hostname.

If you do not want for Exscript to prompt for login details, the
``-i`` switch tells Exscript to not ask for a user and password. You
need to make sure that all hosts have a user and password in the
hostname if you use it.

Reading host names from a text file
-----------------------------------

If you do not wish to hard code the host names or login details into the
command, you may also list the hosts in an external file and load it
using the ``--hosts`` option as follows::

    exscript -c 2 —hosts myhosts.txt test.exscript

Note that *hosts.txt* is a file containing a list of hostnames, e.g.::

    host1
    host2
    ...
    host20

Reading host names from a CSV file
----------------------------------

Similar to the ``--hosts``, you may also use ``--csv-hosts`` option to
pass a list of hosts to Exscript while at the same time providing a
number of variables to the script. The CSV file has the following
format::

    address my_variable another_variable
    telnet://myhost value another_value
    ssh://yourhost hello world

Note that fields are separated using the tab character, and the first
line **must** start with the string "address" and is followed by a list
of column names.

In the Exscript template, you may then access the variables using those
column names::

    ls -l $my_variable
    touch $another_variable

Using Account Pooling
---------------------

You can also pass in a pre-loaded list of accounts from a separate file.
The accounts from the file are used for hosts that do not have a
user/password combination specified in their URL.

::

    exscript -c 2 —hosts myhosts.txt —account-pool accounts.cfg test.exscript

Note that ``accounts.cfg`` is a config file with a defined syntax as
seen in the API documentation for
:func:`Exscript.util.file.get_accounts_from_file`.

It is assumed that you are aware of the security implications of saving
login passwords in a text file.

Logging
-------

Exscript has built-in support for logging - just pass the ``--logdir``
or ``-l`` option with a path to the directory in which logs are stored::

    exscript -l /tmp/logs -c 2 —hosts myhosts.txt —account-pool accounts.cfg test.exscript

Exscript creates one logfile per device. In the case that an error
happened on the remote device, it creates an additional file that
contains the error (including Python's traceback).

Interacting with a device
-------------------------

So far we only fired and forgot a command on a device, there was no true
interaction. But Exscript does a lot to make interaction with a device
easier. The first notable tool is the ``extract`` keyword. Let's look at
an example::

    uname -a{extract /^(\S+)\s+(\S+)/ as os, hostname}

The Exscript Template Language
------------------------------

The Exscript template language is in some ways comparable to Expect, but
has unique features that make it a lot easier to use and understand for
non-developers.

A first example::

    {fail "not a Cisco router" if connection.guess_os() is not "ios"}

    show ip interface brief {extract /^(\S+)\s/ as interfaces}
    configure terminal
    {loop interfaces as interface}
        interface $interface
        description This is an automatically configured interface description!
        cdp enable
        no shut
        exit
    {end}
    copy running-config startup-config

*Exscript* templates support many more commands. Here is another example,
to automate a session with a Cisco router::

    show version {extract /^(cisco)/ as vendor}
    {if vendor is "cisco"}
      show ip interface brief {extract /^(\S+)\s/ as interfaces}
      {loop interfaces as interface}
        show running interface $interface
        configure terminal
        interface $interface
        no shut
        end
      {end}
      copy running-config startup-config
    {end}

Advanced Templates
------------------

Exscript templates support many more commands. For a full overview over
the template language, please check :doc:`templates`.
