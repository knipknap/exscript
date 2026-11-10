Migrating from 2.x to 3.0
=========================

Exscript 3.0 keeps the Python API and the template language. It changes
defaults that were insecure or unreliable, and removes outdated code.
Most scripts run unchanged once they pass the checks in the first
section. The :doc:`changelog` describes every change.

First checks
------------

These changes affect most scripts.

Python 3.12 or later
    Exscript 3.0 runs on Python 3.12 to 3.15. Stay with Exscript 2.x on
    older versions.

SSH is the default protocol
    Hosts without a protocol, e.g. ``router1`` instead of
    ``telnet://router1``, are connected with SSH. For Telnet devices,
    write ``telnet://router1``, or pass ``default_protocol='telnet'`` to
    the function that reads the hosts, e.g.
    :func:`~Exscript.util.file.get_hosts_from_file`,
    :class:`~Exscript.Host` or :func:`~Exscript.protocols.connect`. The
    command line tool has ``--protocol telnet``.

SSH host keys are verified
    Exscript connects only to SSH hosts whose key is in
    ``~/.ssh/known_hosts``. Add your devices, for example with
    ``ssh-keyscan``, or pass ``host_key_policy='auto-add'`` (command line:
    ``--ssh-host-key-policy auto-add``). See :doc:`security`.

Templates run in secure mode
    Templates that call ``sys.exec``, ``sys.env`` or ``file.*`` (except
    ``file.exists``) fail unless you pass ``secure=False`` to
    :func:`Exscript.util.template.eval` and the other functions of that
    module, or the option ``--insecure`` to the command line tool.
    ``sys.exec`` runs the command without a shell and returns text; for
    pipes and redirections, use ``sys.exec("sh -c '...'")``.

``close()`` logs out
    ``close()`` sends the logout command of the driver, ``exit`` on most
    devices, and closes the connection. In 2.x, it waited until the host
    closed the connection, so scripts sent ``exit`` themselves; they still
    work. ``close(force=True)`` closes at once, as before.

Connections
-----------

Terminal size
    Sessions get a terminal of 511 columns and 1000 lines, instead of the
    size of the terminal that runs the script, or 80×25 without one.
    Devices whose driver does not set the width themselves, e.g. Linux
    hosts, no longer wrap lines at 80 characters. For the old size, pass
    ``term_width=80, term_height=25``.

Closed connections
    If the host closes the connection while Exscript waits for a
    response, all protocols raise
    :class:`~Exscript.protocols.exception.ConnectionClosedException`,
    which is a ``ProtocolException`` and an ``EOFError``. Only code that
    expected a ``TimeoutException`` in this case must change.

Error messages
    :class:`~Exscript.protocols.exception.InvalidCommandException`
    contains only the line with the error. The full response is still in
    ``conn.response``.

Key logins
    A failed SSH login with a key raises
    :class:`~Exscript.protocols.exception.LoginFailure`, like a failed
    password login. 2.x raised paramiko's ``AuthenticationException`` or
    ``SSHException``, or an ``OSError`` for an unreadable key file; the
    original error is now the ``__cause__``.

Responses
    ``conn.get_response()`` returns the response without the echo of the
    command, control characters and terminal escape sequences, and with
    ``\n`` line ends. ``conn.response`` is unchanged.

Generic prompt
    A match of the prompt pattern of the generic driver, which the
    ``adtran``, ``aix`` and ``shell`` drivers use, too, counts only if no
    more data arrives within 20 ms.

OS detection
    Signals that several systems show no longer select a driver, so some
    devices are guessed differently, e.g. as ``unknown`` instead of a wrong
    driver. Pass ``driver=`` if a device needs a specific driver. See
    :doc:`drivers`.

Templates
---------

``__response__``
    The functions of the ``connection`` module clean the response like
    ``get_response()``.

``connection.wait_for()``
    No longer consumes the response and the prompt; use
    ``connection.expect()`` for that.

``connection.send()``, ``connection.sendline()``
    Clear ``__response__``.

``connection.close()``
    Logs out first; ``connection.close(true)`` closes at once.

Last line
    A template also sends its last line if the line does not end with a
    line break. 2.x ignored such a line.

``extract``
    Requires a regular expression between slashes. 2.x also accepted a
    string in double quotes, e.g. ``{extract "(a)" as y}``.

Variables of the caller
    Keep their values until a statement of the template changes them. In
    2.x, assignments, ``append``, ``extract`` and ``loop`` reset their
    variables when the template was compiled, e.g. ``append`` and
    ``extract ... into`` started with an empty list.

Operators
    Operators of the same priority are evaluated from left to right, e.g.
    ``10 - 2 - 3`` is 5 and ``0 and 1 or 1`` is 1. 2.x evaluated them from
    right to left. ``and`` and ``or`` have the same priority, so
    ``1 or 0 and 0`` is 0.

``and``, ``or``
    Evaluate the right operand only if the left one does not decide the
    result, as documented. 2.x always evaluated both, e.g. called the
    functions in both.

Command line tool
-----------------

Besides the defaults above: a value entered at a ``-d VAR={#"PROMPT"}``
prompt is parsed as a Python literal, such as a number or a list, instead
of being run as Python code, and ``--sleep`` accepts seconds with an
optional suffix ``m``, ``h`` or ``d`` instead of running ``sleep`` in a
shell.

Python API
----------

Attributes that hold the internal state of the protocol adapters are
private. Use these instead:

.. list-table::
   :header-rows: 1

   * - 2.x
     - 3.0
   * - ``conn.buffer``
     - ``conn.response``, ``conn.get_response()``, ``conn.expect()``,
       ``conn.add_monitor()``
   * - ``conn.auto_driver``, ``conn.manual_driver``
     - ``conn.guess_os()``, ``conn.get_driver()``, ``conn.set_driver()``
   * - ``conn.manual_prompt_re``, ``manual_error_re``,
       ``manual_login_error_re``, ``manual_user_re``,
       ``manual_password_re``
     - ``get_prompt()``/``set_prompt()``, ``get_error_prompt()``/``set_error_prompt()``,
       ``get_login_error_prompt()``/``set_login_error_prompt()``,
       ``get_username_prompt()``/``set_username_prompt()``,
       ``get_password_prompt()``/``set_password_prompt()``
   * - ``conn.proto_authenticated``, ``app_authenticated``,
       ``app_authorized``
     - ``is_protocol_authenticated()``, ``is_app_authenticated()``,
       ``is_app_authorized()``
   * - ``conn.cancel``
     - ``conn.cancel_expect()``
   * - ``conn.log``
     - ``conn.logfile``, the path of the log file; setting it switches
       to another file
   * - ``SSH2.client``, ``shell``, ``sock``, ``Telnet.tn``,
       ``conn.last_account``
     - none; they are internal

Other renamed or removed names:

- ``Exscript.protocols.telnetlib`` is internal and contains only what the
  Telnet adapter needs. Use :class:`Exscript.protocols.Telnet`, or the
  package ``standard-telnetlib`` as a replacement for the telnetlib module
  that Python 3.13 removed.
- ``OsGuesser.data_received()`` and ``protocol_info()`` are
  ``check_received_data()`` and ``check_protocol_info()``.
- ``Exscript.util.template.test_secure()`` is ``test(secure=True)``.
- ``Exscript.util.interact.InputHistory.file`` is ``filename``.
- ``Exscript.util.daemonize``, ``Exscript.util.pidutil`` and
  ``Exscript.util.sigintcatcher`` are removed. Run long-lived scripts
  under a service manager such as systemd.
- ``WorkQueue`` has no ``debug`` argument, and ``set_debug()`` takes
  ``level``. Pass the other arguments by keyword.
- ``parselib.Lexer.expect()`` and ``current_is()`` take ``types``
  instead of ``type``.
- The ``dump1()`` methods of the template interpreter are removed.
- Adapters that subclass ``Protocol`` must pass its arguments by
  keyword; new ones were inserted.

Emulators and test servers
--------------------------

- ``CommandSet.add()`` calls its second argument ``handler`` instead of
  ``response``, and ``VirtualDevice.add_commands_from_file()`` calls
  ``autoprompt`` ``prompt``.
- ``VirtualDevice`` no longer echoes the password, so ``response`` after
  a login to it is empty.
- The test servers ``SSHd`` and ``Telnetd`` run as threads; stop them with
  ``exit()`` and ``join()``. Their ``buf`` attribute and the ``encoding``
  argument of ``Telnetd`` are removed.
- ``Exscript.servers.HTTPd`` and its ``RequestHandler`` are removed; their
  digest authentication never worked on Python 3. Use ``http.server`` from
  the standard library or a web framework.

From the 2.9 development versions
---------------------------------

The 2.9 versions were not released on PyPI. Besides the changes above,
their users should know:

- The OpenTelemetry instrumentation records commands and responses only
  with ``instrument(capture_payload=True)``. Its spans are children of
  the current span, and their attributes and the duration histogram have
  new names; see the :doc:`changelog`.
- ``Exscript.protocols.telnetlib`` lost the methods that the Telnet
  adapter does not use, e.g. ``read_until()`` and ``expect()``.
- A function of a template that raises a ``ProtocolException``, e.g.
  ``connection.execline()`` for a command that the device rejects, stops
  the template with that exception instead of an ``ExecuteError``, as in
  2.x, and ``try`` ignores it.
