.. image:: _static/logo.png
    :target: https://exscript.readthedocs.io

.. image:: https://github.com/knipknap/exscript/actions/workflows/ci.yml/badge.svg?branch=master
    :target: https://github.com/knipknap/exscript/actions/workflows/ci.yml

.. image:: https://img.shields.io/pypi/v/Exscript.svg
    :target: https://pypi.org/project/Exscript/

.. image:: https://img.shields.io/github/stars/knipknap/exscript.svg
    :target: https://github.com/knipknap/exscript

.. image:: https://img.shields.io/github/license/knipknap/exscript.svg
    :target: https://github.com/knipknap/exscript/blob/master/COPYING

What is Exscript?
=================

Exscript is a Python module and a template processor for automating network
connections over SSH, Telnet and NETCONF. We attempt to create the best
possible set of tools for working with network devices over these protocols.

Exscript also provides a set of tools and functions for sysadmins, that
simplify **regular expression matching**, **reporting** by email, **logging**,
or **syslog** handling, **CSV parsing**, **ip address handling**,
**template processing**, and many more.

Exscript may be used to automate sessions with routers from Cisco, Juniper,
OneAccess, Huawei, or any others. If you want to configures machines
running Linux/Unix, IOS, IOS-XR, JunOS, VRP, or any other operating system
that can be used with a terminal, Exscript is what you are looking for.

Using Exscript with Python
--------------------------

Make sure to check out the :doc:`python_tutorial`.
You may also want to look at the
`Python examples <https://github.com/knipknap/exscript/tree/master/demos/>`_.
If you upgrade from Exscript 2.x, read :doc:`migration`.

Using the Exscript command line tool
------------------------------------

Have a look at our :doc:`cli_tutorial`. You will also want to learn about
:doc:`templates`.

Main design goals
-----------------

- Exscript provides **high reliability** and **scalability**. Exscript is
  used by some of the world's largest ISPs to maintain hundreds of thousands
  of sessions every day.
- Exscript is **well tested**: unit tests, replays of sessions recorded
  from devices, and benchmarks run on Linux, macOS and Windows.
- Exscript is **protocol agnostic**, so if you are migrating from Telnet to
  SSH later, you can switch easily by simply changing an import statement.

Development
-----------

Exscript is on `GitHub <https://github.com/knipknap/exscript>`_; see
:doc:`contributing`.

License
-------
Exscript is published under the `MIT licence <https://opensource.org/licenses/MIT>`_.
``Exscript.protocols.telnetlib`` is derived from CPython and published under the
`PSF License 2.0 <https://docs.python.org/3/license.html>`_.

Contents
--------

.. toctree::
   :maxdepth: 2

   install
   python_tutorial
   cli_tutorial
   exscript
   templates
   drivers
   netconf
   security
   platforms
   trouble
   faq
   migration
   api
   changelog
   contributing
