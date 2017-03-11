.. image:: _static/logo.png
    :target: http://exscript.readthedocs.io

.. image:: https://travis-ci.org/knipknap/exscript.svg?branch=master
    :target: https://travis-ci.org/knipknap/exscript

.. image:: https://coveralls.io/repos/github/knipknap/exscript/badge.svg?branch=master
    :target: https://coveralls.io/github/knipknap/exscript?branch=master

.. image:: https://lima.codeclimate.com/github/knipknap/exscript/badges/gpa.svg
    :target: https://lima.codeclimate.com/github/knipknap/exscript
    :alt: Code Climate

.. image:: https://img.shields.io/github/stars/knipknap/exscript.svg
    :target: https://github.com/knipknap/exscript/stargazers

.. image:: https://img.shields.io/github/license/knipknap/exscript.svg
    :target: https://github.com/knipknap/exscript/blob/master/COPYING

|
What is Exscript?
=================

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

Using Exscript with Python
--------------------------

Make sure to check out the :doc:`python_tutorial`.
You may also want to look at the
`Python examples <https://github.com/knipknap/exscript/tree/master/demos/>`_.

Using the Exscript command line tool
------------------------------------

Have a look at our :doc:`cli_tutorial`. You will also want to learn about
:doc:`templates`.

Main design goals
-----------------

- Exscript provides **high reliability** and **scalability**. Exscript is
  used by some of the world's largest ISPs to maintain hundreds of thousands
  of sessions every day.
- Exscript is **extremely well tested**. The Exscript public API has almost
  100% test coverage.
- Exscript is **protocol agnostic**, so if you are migrating from Telnet to
  SSH later, you can switch easily by simply changing an import statement.

Development
-----------

Exscript is on `GitHub <https://github.com/knipknap/exscript>`_.

License
-------
Exscript is published under the `GPLv2 <https://www.gnu.org/licenses/old-licenses/gpl-2.0.txt>`_.

Contents
--------

.. toctree::
   :maxdepth: 2

   install
   python_tutorial
   cli_tutorial
   exscript
   templates
   trouble
   API Documentation<modules>
