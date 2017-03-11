# Exscript

[![Build Status](https://travis-ci.org/knipknap/exscript.svg?branch=master)](https://travis-ci.org/knipknap/exscript)
[![Coverage Status](https://coveralls.io/repos/github/knipknap/exscript/badge.svg?branch=master)](https://coveralls.io/github/knipknap/exscript?branch=master)
[![Code Climate](https://lima.codeclimate.com/github/knipknap/exscript/badges/gpa.svg)](https://lima.codeclimate.com/github/knipknap/exscript)
[![Documentation Status](https://readthedocs.org/projects/exscript/badge/?version=latest)](http://exscript.readthedocs.io/en/latest/?badge=latest)

## Summary

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

## Method 1: Using Exscript with Python

```python
from Exscript.util.start import start
from Exscript.util.file import get_hosts_from_file
from Exscript.util.file import get_accounts_from_file

def do_something(job, host, conn):
    conn.execute('uname -a')

accounts = get_accounts_from_file('accounts.cfg')
hosts = get_hosts_from_file('myhosts.txt')
start(accounts, hosts, do_something, max_threads=2)
```

## Method 2: Using the Exscript command line tool

Create a file named `test.exscript` with the following content:

```
uname -a
```

To run this Exscript template, just start Exscript using the following command:

```
exscript test.exscript ssh://localhost
```

Awesome fact: Just replace `ssh://` by `telnet://` and it should still work with Telnet devices.


## Documentation

Full documentation is here:

http://exscript.readthedocs.io
