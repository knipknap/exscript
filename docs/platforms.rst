Platforms
=========

Exscript runs on Linux, macOS and Windows with Python 3.12 or later. CI
runs the tests with every supported Python version on Linux, with the
latest one on macOS and Windows, and with the free-threaded build of
Python 3.14.

Most of Exscript works the same on every platform: for example, it reads
and writes text files such as templates, host lists and logs as UTF-8
everywhere, and gives sessions the same terminal size. These are the
differences.

Windows
-------

- ``interact()`` gets the keyboard input line by line, because the
  Windows console passes it to Python only after Enter. Arrow keys, Tab
  completion and control keys therefore do not reach the device, and a
  typed line may appear twice, because both the console and the device
  echo it.
- On Linux and macOS, the command line tool runs the connections in a
  child process, so that Ctrl+C stops all of them at once. Windows has no
  ``fork()``, so there Ctrl+C may take effect only after the running
  connections end.
- The template function ``sys.exec`` passes the command line to Windows
  without a shell. Commands that are built into the shell need ``cmd /c``,
  for example ``sys.exec("cmd /c dir")``.
- ``pseudo://`` URLs accept Windows paths, such as
  ``pseudo://C:\devices\router.py``.
- The default known_hosts file is ``%USERPROFILE%\.ssh\known_hosts``
  (:doc:`security`).

The queue's process mode
------------------------

``Queue(mode='multiprocessing')`` needs the ``fork`` start method of
:mod:`multiprocessing`, which is the default only on Linux with Python
3.12 and 3.13. On other platforms and versions, use the default thread
mode, which is also what :func:`Exscript.util.start.start` uses. The
process mode warns that it is not recommended.

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
