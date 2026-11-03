Security
========

Exscript logs in to network devices, often with privileged accounts, so
its defaults are strict. This page explains them, and how to change them
where you need to.

To report a vulnerability, see the `security policy
<https://github.com/knipknap/exscript/security/policy>`_.

SSH host keys
-------------

Before Exscript sends any credentials over SSH or NETCONF, it checks the
host key of the device against ``~/.ssh/known_hosts``, like OpenSSH. On
Windows, the file is ``%USERPROFILE%\.ssh\known_hosts``. Entries for other
ports than 22 have the form ``[host]:port``, and hashed entries work, too.

A key that differs from the known key always raises
:class:`paramiko.BadHostKeyException`: either the device was replaced, or
someone intercepts the connection. For a host without a known key, the
``host_key_policy`` option decides:

``'reject'`` (default)
    Raise :class:`paramiko.SSHException`.

``'warn'``
    Log a warning and accept the key.

``'auto-add'``
    Accept the key and append it to the known_hosts file, like OpenSSH's
    ``StrictHostKeyChecking=accept-new``. Later connections detect a
    changed key.

The best protection is to add the keys before the first connection, and
to compare their fingerprints with the ones that the devices show::

    ssh-keyscan router1 router2 >> ~/.ssh/known_hosts

The options are arguments of the protocol adapters, ``Host`` options, and
command line options::

    from Exscript import Host
    from Exscript.protocols import SSH2

    conn = SSH2(host_key_policy='auto-add', known_hosts='/srv/automation/known_hosts')

    host = Host('ssh://router1')
    host.set_option('host_key_policy', 'auto-add')

.. code-block:: text

    exscript --ssh-host-key-policy auto-add my.exscript router1

``verify_fingerprint=False`` (command line: ``--ssh-auto-verify``) turns
the check off completely. Anyone who can intercept the connection can
then read the credentials, so use it only in isolated labs.

Telnet
------

Telnet sends passwords, commands and responses in clear text. The default
protocol is SSH; use Telnet only for devices that support nothing else,
and only in a trusted management network.

Templates
---------

Templates can come from many authors, so by default they cannot run local
commands or access local files. :func:`Exscript.util.template.eval`,
``eval_file()``, ``paste()``, ``paste_file()``, ``test()`` and
``test_file()`` forbid the template functions ``sys.exec``, ``sys.env``,
and ``file.*`` except ``file.exists``. A template that calls one of them
raises :class:`Exscript.interpreter.exception.PermissionError` when it is
compiled, before anything is sent. Functions that your Python code passes
to the template as variables are always allowed.

For templates that you trust, pass ``secure=False``, or use the command
line option ``--insecure``. ``sys.exec`` runs the command without a shell,
so template variables in the command cannot inject shell commands.

Credentials
-----------

Exscript keeps passwords out of its output: debug logs show them as
``<secret>``, ``repr()`` of an :class:`~Exscript.Account` shows only the
name, and :class:`~Exscript.protocols.exception.InvalidCommandException`
contains only the line with the error, not the whole response.

Where the passwords come from is up to you. In order of preference:

- SSH keys: ``Account('admin', key=PrivateKey.from_file('/home/admin/.ssh/id_ed25519'))``.
- A secret store or the environment of a service, read at run time.
- A prompt: :func:`Exscript.util.interact.read_login`.
- An account pool file (:func:`Exscript.util.file.get_accounts_from_file`,
  command line: ``--account-pool``). Its passwords are only base64
  encoded, which protects nothing: make the file readable only for you.

Logs and recordings
-------------------

Logs contain everything that the devices sent, which may include secrets,
for example in a ``show running-config``. Store them like the
configurations themselves. Before you share a log in an issue, remove
passwords, keys, host names and addresses.

The OpenTelemetry instrumentation (``Exscript[otel]``) records commands
and responses only with ``instrument(capture_payload=True)``. It then
truncates them to ``max_payload_length`` characters and replaces
passwords with ``<secret>``.

XML
---

Exscript parses NETCONF replies without resolving entities, loading DTDs,
or accessing the network. lxml additionally limits the size and depth of
documents; ``conn.huge_tree = True`` lifts these limits for very large
replies, but also the protection against documents that are built to
exhaust the memory. Enable it only for devices that you trust.
