.. Exscript documentation master file, created by
   sphinx-quickstart on Wed Mar  8 19:52:48 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Exscript documentation
======================

Summary
-------

Exscript is a Python module and a template processor for automating network 
connections over protocols such as Telnet or SSH. We attempt to create the 
best possible set of tools for working with Telnet and SSH.

Exscript also provides a set of tools and functions for sysadmins, that
simplify **regular expression matching**, **reporting** by email, **logging**,
or **syslog** handling, **CSV parsing**, **ip address handling**,
**template processing**, and many more.

Exscript may be used to automate sessions with routers from Cisco, Juniper, 
OneAccess, Huawei, or any others. If you want to configures machines 
running Linux/Unix, IOS, IOS-XR, JunOS, VRP, or any other operating system 
that can be used with a terminal, Exscript is what you are looking for.

Method 1: Using Exscript with Python
------------------------------------

::
    from Exscript.util.start import start
    from Exscript.util.file import get_hosts_from_file
    from Exscript.util.file import get_accounts_from_file

    def do_something(job, host, conn):
        conn.execute('uname -a')

        accounts = get_accounts_from_file('accounts.cfg')
        hosts = get_hosts_from_file('myhosts.txt')
        start(accounts, hosts, do_something, max_threads=2)

Make sure to check out the `python_tutorial`.
You may also want to look at the
`Python examples <https://github.com/knipknap/exscript/tree/master/demos/>`_.

Method 2: Using the Exscript command line tool
----------------------------------------------

Create a file named **test.exscript** with the following content::

    uname -a

To run this Exscript template, just start Exscript using the following command::

    exscript test.exscript ssh://localhost

Awesome fact: Just replace `ssh://` by `telnet://` and it should still work with Telnet devices.
Make sure to check out the `cli_tutorial`.

Main design goals
-----------------

- Exscript provides **high reliability** and **scalability**. Exscript is
  used by some of the world's largest ISPs to maintain hundreds of thousands
  of sessions every day.
- Exscript is **extremely well tested**. The Exscript public API has almost
  100% test coverage.
- Exscript is **protocol agnostic**, so if you are migrating from Telnet to
  SSH later, you can switch easily by simply changing an import statement.

License
-------
Exscript is published under the `GPLv2 <https://www.gnu.org/licenses/old-licenses/gpl-2.0.txt>`_.

Contents
--------

.. toctree::
   :maxdepth: 2

   install
   exscript
   python_tutorial
   cli_tutorial
   templates
   trouble
   python
   API Documentation<modules>
