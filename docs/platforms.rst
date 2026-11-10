Platforms
=========

Exscript runs on Linux, macOS and Windows with Python 3.12 or later. CI
runs the tests with every supported Python version on Linux, with the
latest one on macOS and Windows, and with the free-threaded build of
Python 3.14.

Most of Exscript works the same on every platform: for example, it reads
and writes text files such as templates, host lists and logs as UTF-8
everywhere, gives sessions the same terminal size, and its command line
tool stops all connections at once on Ctrl+C. These are the differences.

Windows
-------

- ``interact()`` gets the keyboard input line by line, because the
  Windows console passes it to Python only after Enter. Arrow keys, Tab
  completion and control keys therefore do not reach the device, and a
  typed line may appear twice, because both the console and the device
  echo it.
- The template function ``sys.exec`` passes the command line to Windows
  without a shell. Commands that are built into the shell need ``cmd /c``,
  for example ``sys.exec("cmd /c dir")``.
- ``pseudo://`` URLs accept Windows paths, such as
  ``pseudo://C:\devices\router.py``.
- The default known_hosts file is ``%USERPROFILE%\.ssh\known_hosts``
  (:doc:`security`).

Threads, processes and asyncio
------------------------------

The queue runs each job in a thread; Exscript 3.0 removed its process
mode. To use several CPU cores, run the free-threaded build (below), or
start several processes yourself, for example with a pool of
:mod:`concurrent.futures` or the prefork pool of Celery, and create the
queue or the connections in the child processes.

Exscript also runs under `gevent <https://www.gevent.org>`_, which
replaces threads with greenlets, so a process can hold many more
connections. The application patches the standard library itself, before
it imports anything else::

    from gevent import monkey

    monkey.patch_all()

    from Exscript import Queue  # and the rest

Exscript has no gevent dependency or setting; CI runs Telnet and SSH
sessions through a queue under gevent. gevent does not support the
free-threaded build.

From :mod:`asyncio` code, run Exscript in a thread, so that it does not
block the event loop::

    result = await asyncio.to_thread(conn.execute, 'show version')

Free-threaded Python
--------------------

Exscript works on the free-threaded build of Python 3.14 (``python3.14t``),
where threads, and so connections in a queue, run in parallel. NETCONF
uses lxml, which does not declare support for free threading yet: when
the first NETCONF session starts, Python enables the global interpreter
lock and warns, unless it runs with ``PYTHON_GIL=0``. Exscript loads lxml
only for NETCONF, so other protocols keep running without it.

Threads and connections
-----------------------

Use each connection from one thread at a time, as the queue does: it
gives each host its own connection. A connection that another thread
closes while it waits for data may raise an exception instead of
reporting the closed connection.
