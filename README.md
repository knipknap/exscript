# Exscript

<!-- TODO: Readme links need to be reviewed. -->
[![Build Status](https://travis-ci.org/knipknap/exscript.svg?branch=master)](https://travis-ci.org/knipknap/exscript)
[![Coverage Status](https://coveralls.io/repos/github/knipknap/exscript/badge.svg?branch=master)](https://coveralls.io/github/knipknap/exscript?branch=master)
[![Code Climate](https://lima.codeclimate.com/github/knipknap/exscript/badges/gpa.svg)](https://lima.codeclimate.com/github/knipknap/exscript)
[![Documentation Status](https://readthedocs.org/projects/exscript/badge/?version=latest)](http://exscript.readthedocs.io/en/latest/?badge=latest)
[![Reviewed by Hound](https://img.shields.io/badge/Reviewed_by-Hound-8E64B0.svg)](https://houndci.com)

## Summary

Exscript is a Python package and a template processor for automating network connections
CLI-driven over protocols such as Telnet, SSH or alternatively structured Netconf. We
attempt to create the best possible set of tools for working with Telnet, SSH and
Netconf.

Exscript also provides a set of tools and functions for sysadmins, that
simplify **regular expression matching**, **reporting** by email, **logging**,
or **syslog** handling, **CSV parsing**, **ip address handling**,
**template processing**, and many more.

Exscript may be used to automate sessions with routers from Cisco, Juniper, OneAccess,
Huawei, or any others. If you want to configures machines running Linux/Unix, IOS,
IOS-XR, JunOS, VRP, or any other operating system that can be used with a CLI terminal,
Exscript is what you are looking for. Additionally any system that supports SSH Netconf
1.0 and 1.1 can be automated with Exscript.

## Do you need commercial support?

<!-- TODO: Does "Procedure 8" for commercial support exist? -->
Exscript is supported by [Procedure 8](https://procedure8.com). Get in touch if you need
anything!

## Method 1: Using Exscript with Python

### Simple

```python
from Exscript.protocols import SSH2
from Exscript.util.interact import read_login

conn = SSH2()
conn.connect('localhost')
conn.login(read_login())
conn.execute('uname -a')
```

### Slightly more advanced (multi threaded)

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

```plaintext
uname -a
```

To run this Exscript template, just start Exscript using the following command:

```shell
exscript test.exscript ssh://localhost
```

Awesome fact: Just replace `ssh://` by `telnet://` and it should still work with Telnet
devices. This also works for Netconf, just use `netconf://` instead and create a valid
Netconf template:

```xml
<rpc>
    <!-- your XML RPC body -->
</rpc>
```

The RPC body will be sent to the device, automatically encapsulated with proper
rpc-tags like:

```xml
<rpc xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="...">
    <!-- your XML RPC body -->
</rpc>`
```

No need to handle the message-id and namespaces manually. The reply will be available as
plaintext (like with CLI) or a parsed XML tree element.

## Release-Management

Releases are created on demand without any strict interval. The versioning follows the
packaging guidance for Python and supports the following canonical-like tag pattern,
optionally with local version specifiers, for the build process.

```plaintext
N.N(.N)?[{a|b|rc}N][.postN][.devN][+{a..z0..9}(.{a..z0..9})*]
```

See also: [Python version-specifiers](https://packaging.python.org/en/latest/specifications/version-specifiers)

## Documentation

Full documentation is here: http://exscript.readthedocs.io
