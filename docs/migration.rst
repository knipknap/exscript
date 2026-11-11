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
    Sessions get a terminal of 510 columns and 1000 lines, instead of the
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
    ``\n`` line ends. ``conn.response`` no longer ends with the ``\r`` of
    the line break before the prompt, and ``send()`` sets it to ``None``.
    :func:`~Exscript.util.match.first_match` and
    :func:`~Exscript.util.match.any_match` search ``conn.get_response()``
    when they get a connection; pass ``conn.response`` to search it as
    before.

Errors in ``expect()``
    ``expect()`` raises
    :class:`~Exscript.protocols.exception.InvalidCommandException` if a
    line of the response matches an error pattern, as ``expect_prompt()``
    does; 2.x checked only in ``expect_prompt()``. The data is consumed all
    the same, so catch the exception where such a line is expected.

Debug output
    The messages of ``debug=`` and of ``Queue(verbose=2)`` and higher go to
    Python's :mod:`logging`, to loggers such as ``Exscript.protocols.ssh2``
    and ``Exscript.queue``, instead of to ``stderr`` and ``stdout``.
    Configure logging to see them, e.g. with
    ``logging.basicConfig(level=logging.DEBUG)``.

``connect()``
    Raises a ``ProtocolException`` if the adapter is connected already;
    call ``close()`` first.

Connect rate limit
    Connects to the same host are spaced by 1.1 seconds by default. Pass
    ``connect_rate_limit=0`` to connect at once, as 2.x did.

Generic prompt
    A match of the prompt pattern of the generic driver, which the
    ``adtran``, ``aix`` and ``shell`` drivers use, too, counts only if no
    more data arrives within 20 ms.

OS detection
    Signals that several systems show no longer select a driver, so some
    devices are guessed differently, e.g. as ``unknown`` instead of a wrong
    driver. Pass ``driver=`` if a device needs a specific driver. See
    :doc:`drivers`.

Driver names
    A driver name that does not exist raises a ``TypeError`` in the
    constructor, e.g. ``SSH2(driver='iosxr')``, also through the ``driver``
    option of a ``Host`` and ``--use-driver``. 2.x ignored it and guessed
    the driver.

NX-OS errors
    The ``nxos`` driver recognizes the error messages of NX-OS: the parser
    errors, which end with ``at '^' marker.``, such as
    ``% Invalid command at '^' marker.``, then
    ``% Permission denied for the role``, and lines that start with
    ``ERROR:`` or ``Error:``. So ``execute()`` raises
    :class:`~Exscript.protocols.exception.InvalidCommandException` for the
    commands that NX-OS rejects with them; 2.x returned their response.
    Catch the exception where a command may fail.

Login without flush
    With the ``nxos``, ``bigip`` and ``rios`` drivers,
    ``login(flush=False)`` leaves the prompt in the buffer, as with the
    other drivers; 2.x consumed it. Consume it, e.g. with
    ``expect_prompt()``, before the first command, or omit ``flush=False``.

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

Escape sequences
    Commands and strings evaluate escape sequences such as ``\t``,
    ``\x41`` or ``\u00e4``, e.g. ``show \x41`` sends ``show A``; in 2.x, a
    backslash only made the next character literal. Escape the backslash,
    as in ``\\x41``, or pass ``no_escaping=True`` to
    :func:`~Exscript.util.template.eval`, ``eval_file()``, ``paste()`` or
    ``paste_file()`` (command line: ``--no-escaping``) for the old
    behavior; with it, ``\t`` in a string is still a tab.

Comments
    A hash behind an escaped character is text: ``show \}# x`` sends
    ``show }# x``; 2.x sent ``show }``.

``<rpc>`` elements
    A template sends the content of an ``<rpc>`` element as a command of
    its own, without the tags, for NETCONF. To send the tags as text,
    escape them: ``\<rpc>``, ``\</rpc>``.

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

Values of the caller
    A string that a function of the caller returns, or a dict that the
    caller passes, is one item: ``in``, ``loop`` and ``extract`` no longer
    use its characters or keys. Return and pass lists instead. A tuple is
    a list: ``$t`` gives its items, one per line, instead of the text of
    the tuple, and ``{x = t}`` copies the items instead of storing the
    tuple as one item.

Errors of functions
    An exception of a function, other than a
    :class:`~Exscript.protocols.exception.ProtocolException`, stops the
    template with an :class:`~Exscript.parselib.exception.ExecuteError`
    that shows the position of the call; the exception of the function is
    its ``__context__``. 2.x raised the exception of the function. ``$f``
    for a function ``f`` in a command or a string raises an
    ``ExecuteError``, too; 2.x inserted the text of the function object.

Command line tool
-----------------

Besides the defaults above: a value entered at a ``-d VAR={"PROMPT"}``
prompt is text instead of being run as Python code, so enter it without
quotes; for a number or a list, write ``-d VAR={#"PROMPT"}``, which
parses a Python literal. ``--sleep`` accepts seconds with an optional
suffix ``m``, ``h`` or ``d`` instead of running ``sleep`` in a shell. The
debug messages of ``-v 2`` and higher go to the standard error.

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
       ``conn.last_account``, ``conn.driver_replaced``,
       ``Dummy.init_done``
     - none; they are internal

Other renamed or removed names:

- ``Exscript.protocols.telnetlib`` is internal and contains only what the
  Telnet adapter needs. Use :class:`Exscript.protocols.Telnet`, or the
  package ``standard-telnetlib`` as a replacement for the telnetlib module
  that Python 3.13 removed.
- ``OsGuesser.data_received()`` and ``protocol_info()`` are
  ``check_received_data()`` and ``check_protocol_info()``. Its attributes
  ``info``, ``os_map``, ``auth_os_map``, ``protocol_os_map`` and
  ``auth_buffer`` are private; use ``get()`` and ``set()``.
  ``conn.os_guesser`` is read-only.
- ``Exscript.util.template.test_secure()`` is ``test(secure=True)``.
- ``Exscript.util.interact.InputHistory.file`` is ``filename``.
- ``Exscript.util.daemonize``, ``Exscript.util.pidutil``,
  ``Exscript.util.sigint`` and ``Exscript.util.sigintcatcher`` are
  removed. Run long-lived scripts under a service manager such as systemd.
  To stop the connections of a queue at once on Ctrl+C, as
  ``SigIntWatcher`` did, end the process with ``os._exit()`` in a handler
  of ``signal.SIGINT``.
- ``WorkQueue`` has no ``debug`` argument, and ``set_debug()`` requires
  ``level``. Pass the other arguments by keyword.
- ``Queue(mode='multiprocessing')`` raises a ``ValueError``: jobs run in
  threads only. For several CPU cores, see :doc:`platforms`.
- ``Exscript.account.AccountProxy``, ``Exscript.logger.LoggerProxy``,
  ``Exscript.workqueue.job.Process`` and ``Queue.pipe_handlers`` are
  removed; jobs use the accounts and the loggers directly.
- ``WorkQueue.queue_empty_event`` is emitted when the last job of the queue
  has ended, and no longer when the queue stops. Code that used it to learn
  that the queue stopped continues after ``shutdown()`` or ``join()``
  returns instead.
- ``parselib.Lexer.expect()`` and ``current_is()`` take ``types``
  instead of ``type``.
- The ``dump1()`` methods of the template interpreter are removed, and so
  are the attributes that only its old ordering of operators used:
  ``ExpressionNode.parent_node``, the ``prio`` argument of
  ``Expression.prioritize()``, and ``lft``, ``rgt``, ``op`` and
  ``priority()`` of ``Term``.
- ``string_re`` of ``Exscript.interpreter.string`` is ``varstring_re``;
  ``bracket_re`` and ``Regex.n_groups`` of ``Exscript.interpreter.regex``
  are replaced by ``Regex.groups``. ``HPProCurveDriver.clean_res_re`` is
  removed.
- :func:`~Exscript.util.file.get_accounts_from_file` decodes the
  passwords as UTF-8; 2.x decoded them as latin-1. For non-ASCII passwords
  that were encoded as latin-1, pass ``password_encoding='latin-1'``.
- ``SSH2.get_banner()`` returns the banner as text instead of bytes.
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
- ``SSHd`` without ``key`` creates a host key of its own instead of using
  ``~/.ssh/id_rsa``. To keep a fixed host key, e.g. for ``known_hosts``,
  pass ``key=PrivateKey.from_file(...)``.
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
- ``Netconf.execute()`` raises
  :class:`~Exscript.util.xml.XMLValidationError` instead of lxml's
  ``XMLSyntaxError`` if the RPC body is not one XML element, e.g.
  ``<get-config/><get/>``.
- If a reply has warnings before an error, the raised
  :class:`~Exscript.protocols.exception.RPCError` is the first error, not
  the first warning; its ``errlist`` still holds all of them.
- ``set_timeout()`` after the login also changes how long ``Netconf``
  waits for the reply to an RPC; before, the timeout of the login
  applied.
- If the server closes a NETCONF session, ``execute()`` raises
  :class:`~Exscript.protocols.exception.ConnectionClosedException`
  instead of a plain ``ProtocolException``. It is a ``ProtocolException``
  and an ``EOFError``.
- ``Netconf`` always uses UTF-8, whatever ``encoding`` is passed. With
  the default ``latin-1``, the 2.9 versions showed non-ASCII text as
  mojibake, e.g. ``ZÃ¼rich``, in ``response`` and the logs. Bytes that
  are no UTF-8, e.g. in a latin-1 SSH banner, become U+FFFD.
  ``Netconf.reassemble_chunks()`` counts the chunk sizes in bytes.
