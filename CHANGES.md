# Changelog

## 3.0.0 (unreleased)

Work in progress: the entries below cover the changes merged from the 2.9 development
line and are completed against Exscript 2.6.32 before the release. Breaking changes are
marked with **BREAKING**; a migration guide will accompany the release.

## General

- **License Labels:** Exscript remains MIT-licensed. `Exscript.protocols.telnetlib` is
  derived from CPython's telnetlib (3.12), so it carries the PSF notice, the license text is
  in `LICENSES/PSF-2.0.txt`, and the package declares `MIT AND PSF-2.0`.
- **UTF-8 Files:** Exscript reads and writes text files, e.g. templates, host lists
  and log files, as UTF-8 on every platform, as Python 3.15 does by default. Before,
  it used the encoding of the locale, e.g. cp1252 on Windows, where writing device
  output to a log file could fail.
- **BREAKING - Python 3.12 or Later:** Exscript runs on Python 3.12 to 3.15 and on the
  free-threaded build of 3.14, on Linux, macOS and Windows. Python 2.7 and Python 3
  versions before 3.12 are no longer supported.
- **Type Annotations:** Exscript is annotated and ships the `py.typed` marker (PEP 561),
  so type checkers such as mypy and pyright check the code that uses it. All modules
  pass `mypy --strict`, except the queue (`Exscript.queue`, `Exscript.workqueue`) and
  `Exscript.util.sigint`, which are annotated only in part.
- **Dependencies:** `future` and `configparser`, backports for Python 2, are no longer
  needed. paramiko 3.4 to 5.x is supported (before: 1.17 to 4.x). New: ncclient and
  lxml 5.0 or later, for NETCONF.
- **NETCONF Protocol:** The new adapter `Exscript.protocols.Netconf` (scheme
  `netconf://`, port 830) sends RPCs over SSH with ncclient, and returns the replies as
  text or as lxml elements; an `<rpc-error>` raises `RPCError`. The IOS XR and Junos
  drivers recognize their devices by the NETCONF capabilities.
- **BREAKING - Internal Attributes and Helpers:** Attributes and helpers that were
  meant for internal use are private or removed; the migration guide lists their
  public replacements. Among them are the attributes `buffer`, `auto_driver`,
  `manual_driver`, `manual_*_re`, `*_authenticated`, `last_account`, `cancel` and `log`
  of the protocol adapters, `SSH2.client`, `shell` and `sock`, and `Telnet.tn`;
  `OsGuesser.data_received()` and `protocol_info()`, now `check_received_data()` and
  `check_protocol_info()`; `Exscript.util.template.test_secure()`, now
  `test(secure=True)`; `InputHistory.file`, now `filename`; the `debug` argument of
  `WorkQueue`, whose `set_debug()` argument is now `level`; the `type` argument of
  `parselib.Lexer.expect()` and `current_is()`, now `types`; and the `dump1()` methods
  of the template interpreter.
- **OpenTelemetry Tracing (optional):** Install the `otel` extra (`Exscript[otel]`)
  and call `Exscript.contrib.otel.ExscriptInstrumentor().instrument()`. Every call of
  `connect()`, `login()`, `authenticate()`, `send()`, `execute()` and `close()` creates
  a client span such as `SSH2 execute`, with the attributes `server.address`,
  `server.port`, `exscript.protocol`, `exscript.operation`, `exscript.os` and
  `error.type`. The histogram `exscript.client.operation.duration` records the
  durations in seconds. Commands and responses may contain secrets, so they are
  recorded only with `instrument(capture_payload=True)`: truncated to
  `max_payload_length` characters (default 1024), and with passwords as `<secret>`.
  The extra installs only the OpenTelemetry API; the application provides the SDK.

  Changes against the 2.9 development versions: spans are children of the current
  span instead of the `connect` span, which also ended only on `close()`; the
  `protocol.*` attributes are replaced by the ones above; payloads are no longer
  recorded by default; and the histogram `exscript.client.duration` in milliseconds
  is replaced. `login(account)` with a positional account no longer crashes.

## Security

- **BREAKING - SSH Host Key Verification:** `SSH2` and `Netconf` now verify the host
  key before any credentials are sent. Before, known_hosts was read only after the
  check, and unknown keys were accepted silently. The key is checked against
  `~/.ssh/known_hosts` or the file given with the new `known_hosts` argument,
  including `[host]:port` entries for other ports than 22 and hashed entries. A
  changed key raises `paramiko.BadHostKeyException`. For a host without a known key,
  the new `host_key_policy` argument decides:

  - `'reject'` (default): raise `paramiko.SSHException`;
  - `'warn'`: log a warning and accept the key;
  - `'auto-add'`: accept the key and append it to known_hosts, like OpenSSH's
    `StrictHostKeyChecking=accept-new`.

  Accepted keys are pinned for reconnects of the same object. `verify_fingerprint=False`
  still disables the verification completely. Both new arguments are also `Host`
  options, and the CLI has `--ssh-host-key-policy`.

  To migrate, add the hosts to known_hosts (for example with `ssh-keyscan`), or pass
  `host_key_policy='auto-add'` or `host_key_policy='warn'`.
- **Passwords in Debug Logs:** Passwords and S/Key responses sent by the app-level
  login are logged as `<secret>`. Before, debug level 4 logged them in clear text.
  Debug levels above 5 no longer turn on paramiko's packet dumps, which showed the
  password of an SSH login in clear text.
- **BREAKING - `InvalidCommandException` Message:** The message contains only the
  line that matched an error pattern, for example `Error in the response from the
  device: % Invalid input detected`. Before, it contained the full response, which
  may include configuration secrets. The full response is still in `conn.response`.
- **`repr(Account)`:** Shows only the account name, for example `Account('admin')`.
- **BREAKING - Templates Run in Secure Mode:** `Exscript.util.template.eval()`,
  `eval_file()`, `paste()`, `paste_file()`, `test()` and `test_file()` forbid the
  template functions that run local commands or access local files: `sys.exec`,
  `sys.env`, and `file.*` except `file.exists`. Templates that call them raise
  `Exscript.interpreter.exception.PermissionError` when they are compiled. Functions
  that the caller passes as template variables are allowed. Before, secure mode was
  available only for `test()` and off by default. To migrate, pass `secure=False`,
  or use the new CLI option `--insecure`.
- **BREAKING - `sys.exec` Without a Shell:** The template function `sys.exec` runs
  the command without a shell and waits for it to finish. Pipes, redirections and
  shell variables no longer work; use for example `sys.exec("sh -c '...'")`.
- **XML Parsing:** Exscript parses NETCONF RPCs and replies without resolving
  entities, loading DTDs, or accessing the network, also with `huge_tree`. lxml 5.0 or
  later is required, which no longer resolves external entities by default, also in
  the parsers of ncclient.
- **CLI Without `eval()` and Shell:** A value entered at a `-d VAR={#"PROMPT"}` prompt
  is parsed as a Python literal, such as a number or a list, instead of being run as
  Python code. `--sleep` no longer runs the `sleep` command in a shell; it accepts
  seconds with an optional suffix `m`, `h` or `d`, also on Windows.

## Protocols

- **BREAKING - Default Protocol:** The default protocol changed across all relevant
  entry points/methods from `telnet` to `ssh` (version 2). This change was made to
  improve security and performance. This was an explicit decision as SSH2 should be
  considered the best-practice nowadays. The following entry points are affected:

  - `Exscript.Host(uri, default_protocol='ssh')`
  - `Exscript.protocols.prepare(host, default_protocol='ssh', ...)`
  - `Exscript.protocols.connect(host, default_protocol='ssh', ...)`
  - `Exscript.util.cast.to_host(host, default_protocol='ssh', ...)`
  - `Exscript.util.cast.to_hosts(hosts, default_protocol='ssh', ...)`
  - `Exscript.util.file.get_hosts_from_csv(filename, default_protocol='ssh', ...)`
  - `Exscript.util.file.get_hosts_from_file(filename, default_protocol='ssh', ...)`
  - `Exscript.util.url.Url.from_string(url, default_protocol='ssh')`
  - `exscript` CLI: `-p`/`--protocol`

### Connecting

- **Connect Rate Limit Per Host:** `connect_rate_limit` no longer delays connects to
  other hosts. The limiter slept while it held a process-wide lock, so one waiting
  connect blocked all others, by default for up to 1.1 seconds. Concurrent connects
  to the same host are now spaced, too; before, they could start together.
- **Fewer SSH Reconnects:** Drivers that reconnect between authentication methods
  (`ios`) now reconnect only after a method sent a request that failed. Before, they
  reconnected before every method, also before the public key methods when there was
  no key: a password login to an IOS device that also offers public keys and
  keyboard-interactive took 5 SSH connections, now 3.
- **All Addresses for SSH:** SSH and NETCONF connections try all addresses of the
  host, e.g. IPv4 if IPv6 fails, as Telnet does; before, they tried only the first.
- **SSH Algorithms and Authentication Methods:** The new options
  `disabled_algorithms` and `preferred_authentications` (also `Host` options; CLI:
  `--ssh-disabled-algs` and `--ssh-preferred-auth`) turn off SSH algorithms that a
  device offers but does not handle correctly (passed to paramiko's `Transport`), and
  choose the authentication methods and their order, like OpenSSH's
  `PreferredAuthentications`. The default order is `publickey`,
  `keyboard-interactive`, `password`; methods that the server does not offer are
  skipped.
- **SSH Key Fingerprints in Debug Logs:** The keys that are tried for a login are
  logged with their SHA256 fingerprints, as `ssh-add -l` and `ssh-keygen -l` show
  them. Before, the MD5 fingerprint was logged as a Python bytes literal.
- **SSH Banners in Another Encoding:** An authentication banner or a version string
  that is not valid in the encoding of the connection no longer fails the login; the
  invalid bytes become U+FFFD. Before, e.g. a latin-1 banner with `encoding='utf-8'`
  raised a `UnicodeDecodeError`.
- **Keyboard-Interactive Logins:** Every prompt gets an answer: password prompts the
  password, S/Key challenges the one-time password, other prompts, e.g. for a
  verification code, an empty string. Before, other prompts got no answer, and
  OpenSSH servers closed the connection. All prompts are passed to the received data.
  The password is also no longer sent to a keyboard-interactive prompt that does not
  look like a password prompt when a server refuses the password method (paramiko's
  fallback).
- **SSH Logins With Several Methods:** Servers that require more than one
  authentication method, e.g. OpenSSH's `AuthenticationMethods publickey,password`,
  are supported: after a partial success, the login continues with the methods that
  the server allows next, without reconnecting. Before, it stopped after the first
  method and then failed to open the shell. The key of an account
  (`Account(..., key=...)`) is tried without the password of the account, so such a
  login fails with a `LoginFailure` that names the required methods. Thanks to
  u1735067 (pull request #203), whose rewrite of the authentication included this.
- **BREAKING - Key Logins Raise `LoginFailure`:** A key login that fails raises
  `LoginFailure`, as a password login does, with the original error as its cause.
  Before, it raised paramiko's `AuthenticationException` or `SSHException` when the
  server rejected the key, and an `OSError` when the key file could not be read, so
  `autologin(attempts=...)` did not retry key logins.
- **SSH Keys Without Files:** `PrivateKey.from_string()` creates a key from its text, in
  the format of a key file, e.g. a key from a secret store, which then never needs to
  be written to a file (upstream issue #209). The type is detected unless it is given.
- **BREAKING - Terminal Size:** SSH and Telnet sessions get a terminal of 511 columns
  and 1000 lines; the new options `term_width` and `term_height` (also `Host`
  options) choose another size. Before, Exscript used the size of the terminal that
  ran the script, or 80×25 without one (cron, services), so the same script could
  get differently wrapped output. Where the driver does not set the width or turn
  off paging itself, e.g. on Linux hosts, NX-OS, EOS, VRP or unknown devices, long
  lines are no longer wrapped or cut at 80 characters, and pagers stop only after
  1000 lines. `interact()` still uses the size of the local terminal. For the
  previous behavior without a terminal, pass `term_width=80, term_height=25`.
- **Reliable `close()`:** `close()` closes the connection and resets the object even
  if the logout fails. Errors of the logout and while closing, e.g. because the host
  closed the connection first, are only logged (debug level 1); before, errors of
  the logout were ignored silently, and `close(force=True)` could raise an
  `EOFError`.

### Interactive Shell

- **`interact()` Fixes:** Typed characters of several bytes, e.g. umlauts on a UTF-8
  terminal, no longer crash the session. Telnet commands from the host are processed
  instead of shown, and typed text is sent like with `send()`, so Telnet escapes the
  byte 255. The previous `SIGWINCH` handler is restored when the session ends. On
  Windows, the thread that receives no longer keeps the process alive.

### Waiting for Responses

- **One Implementation for All Protocols:** `expect()`, `waitfor()`, `expect_prompt()`
  and `execute()` work the same for SSH, Telnet, NETCONF and the dummy protocol, and
  the adapters read up to 64 KiB at a time:
  - patterns that end with `$` or `\Z`, like most driver prompts, are searched in the
    last 1024 characters of the received data (before: 150);
  - other patterns are searched in all data received since the last match. Before,
    SSH searched only the last 150 characters after each read, so it missed a match
    that was followed by more output in the same read and waited until the timeout.
    Telnet found it, because it read 64 bytes at a time;
  - a large response is searched once instead of after every read: `execute()` with a
    4 MiB response takes 0.6 seconds of CPU time over Telnet instead of 4.3.
- **BREAKING - `ConnectionClosedException`:** If the host closes the connection while
  Exscript waits for a response, all protocols raise the new
  `Exscript.protocols.exception.ConnectionClosedException`. Before, SSH raised a
  `ProtocolException`, and Telnet an `EOFError`, or a `TimeoutException` if unmatched
  data was left. The new exception is a `ProtocolException` and an `EOFError`, so only
  code that expects a `TimeoutException` for a closed connection must change.
- **Login Errors After Sending Only:** `login()`, `app_authenticate()` and
  `app_authorize()` raise `LoginFailure` only if the driver's login error patterns
  match data that arrived after Exscript sent something, e.g. the password. Before,
  a banner such as "Access denied for unauthorized users" failed the login before any
  credentials were sent. A login error is detected with the next prompt, when the host
  closes the connection, or at the timeout.
- **Prompts After Escape Sequences:** A prompt after terminal escape sequences is
  found now, e.g. after bash's `ESC[?2004h` (bracketed paste mode, with a `termtype`
  other than the default `dumb`) or a window title; before, `login()` timed out.
  Patterns are matched against the received text first, so patterns that contain
  escape sequences match as before.
- **Settle Time for the Generic Prompt:** The prompt pattern of the generic driver,
  which the `adtran`, `aix` and `shell` drivers use too, also matches output lines such
  as FRR's route codes (`S>`). Its match now counts only if no more data arrives
  within 20 ms, so each prompt over these drivers takes 20 ms longer. The prompts of
  the other drivers, and prompts set with `set_prompt()`, count at once.
- **Monitors:** The callbacks of `add_monitor()` no longer miss matches after
  `expect()` consumed the data before them. Monitors search only the end of the
  received data instead of a copy of all of it for each read: 8 MiB of output in
  1 KiB reads take 0.015 seconds instead of 9.4. The positions in the match object
  that the callback gets refer to the searched text, not to the whole buffer.
- **NETCONF 1.1 Chunks:** `Netconf.reassemble_chunks()` takes linear time: a 16 MiB
  reply in 4 KiB chunks takes 0.02 seconds instead of 5.2.
- **NETCONF Threads:** ncclient's thread appends the received data to the buffer that
  the caller searches. The buffer is locked now; before, a search could move the
  position at which the thread wrote. Exscript still sends its `<hello>` and RPCs
  pretty-printed, but no longer makes other users of ncclient in the same process do
  so (changes against the 2.9 development versions).
- **Free-Threaded Python:** `import Exscript` no longer imports lxml and ncclient;
  NETCONF sessions and templates with RPCs load them when they need them. lxml
  enables the GIL of free-threaded Python (3.14t), so before, Exscript always ran with
  the GIL there. XML is parsed with a new parser for each call, so threads no longer
  wait for each other.

### Telnet

- **Telnet Client Based on CPython 3.12:** `Exscript.protocols.telnetlib` is now based
  on the last telnetlib of CPython (3.12; the module was removed in 3.13). Fixes:
  - connections use IPv6, too, and try all addresses of the host;
  - Telnet commands are parsed in whole reads instead of byte by byte, which cuts the
    CPU time of large responses by about a quarter;
  - a command split across two reads no longer blocks until more data arrives;
  - `IAC NOP` and option code 0 no longer crash the connection with a `TypeError`; a
    `DO` for option 0 is refused with `WONT` instead of being ignored;
  - subnegotiations end at `IAC SE` only, as RFC 855 requires;
  - multibyte characters split across reads are decoded correctly, e.g. with
    `encoding='utf-8'`;
  - sent data is written completely (`sendall()`), and window sizes that contain
    the byte 255 are escaped;
  - passwords are no longer logged at debug level 5.
- **BREAKING - `Exscript.protocols.telnetlib` Is Internal:** The module contains only
  what the Telnet adapter uses. Removed: the methods `read_until()`, `read_some()`,
  `read_eager()`, `read_very_eager()`, `read_lazy()`, `read_very_lazy()`, `read_all()`,
  `expect()`, `waitfor()`, `interact()` and `mt_interact()` with their helpers,
  `sock_avail()`, `get_socket()`, `fileno()` and `set_receive_callback()`; the
  attribute `cancel_expect`; the function `test()`; the option constants other than
  those Exscript negotiates; and the `stdout` and `stderr` arguments. The new method
  `receive(timeout)` reads once and passes the text to the callback. The remaining
  constants are integers instead of bytes, and the options of the constructor are
  keyword-only. Use `Exscript.protocols.Telnet`. If you need a drop-in replacement for
  the telnetlib module that Python 3.13 removed, use the package `standard-telnetlib`.
- **Closing While Receiving:** If `close()` of `Exscript.protocols.telnetlib.Telnet`
  runs in another thread while `receive()` waits for data, the connection stays
  closed, and `receive()` returns `False`. Before, data that arrived in the meantime
  cleared the end-of-file flag, and the next `receive()` failed with
  `AttributeError: 'NoneType' object has no attribute 'settimeout'`.

### NETCONF

The `Netconf` adapter is new in 3.0, so these fixes matter only to users of the 2.9
development versions; "before" refers to them.

- **`close()` Ends ncclient's Thread:** `close()` ends the thread in which ncclient reads
  the session, also with `force=True` or if the server does not answer
  `<close-session/>`. Before, the thread then kept running until the process ended, and
  `close()` waited 0.3 seconds for it in vain.
- **RPC Body of One Element:** `execute()` and `send()` raise `XMLValidationError`
  before sending if the RPC body is not one XML element, e.g. `<get-config/><get/>` or
  text. Before, they raised lxml's `XMLSyntaxError`.
- **`RPCError` After Warnings:** The raised `RPCError` is the first `<rpc-error>` of the
  reply with the severity `error`; `errlist` holds all of them, warnings too, in their
  order. Before, it was the first one, which could be a warning.
- **`set_timeout()` After the Login:** RPCs, also the `<close-session/>` of `close()`,
  wait for their reply as long as the current timeout says. Before, they kept the
  timeout of the login, so `set_timeout()` after `login()` did not change it.
- **Closed Sessions:** If the server closes the session, also during an RPC, `execute()`
  raises `ConnectionClosedException`, like SSH and Telnet. Before, it raised a plain
  `ProtocolException` ("ncclient related error ..."); the new exception is a
  `ProtocolException`, too.
- **UTF-8:** `Netconf` always uses UTF-8, which RFC 6241 requires for NETCONF messages,
  whatever `encoding` is passed, and `reassemble_chunks()` counts the chunk sizes in
  bytes, as RFC 6242 does. Bytes that are no UTF-8, also in the SSH banner, become
  U+FFFD. Before, non-ASCII text showed as mojibake in `response`, the standard output
  and the logs with the default encoding latin-1, and with `encoding='utf-8'`,
  NETCONF 1.1 replies with non-ASCII text failed to reassemble.

### Protocol Drivers

- **Generic Prompt Pattern in Linear Time:** The prompt pattern of the generic driver,
  which other drivers inherit, backtracked catastrophically on long lines that are no
  prompt: a line with a run of 100 word characters took 1.3 seconds to check, 200
  characters 25 seconds, so hex or base64 output could stall a session. The pattern
  matches the same strings, verified against the old one, in linear time. A test
  checks every driver pattern for this. The isam driver's prompt pattern, which the
  OS guesser runs on all received data, matches the same strings 3.5 times faster.

- **BREAKING - More Accurate OS Guessing:** On the test corpus (60 device banners and
  5 recorded sessions), `guess_os()` is right for 213 of 245 sessions instead of 204,
  and no guess that was right changed. Signals that other systems show, too, no
  longer select a driver:
  - `isam` claimed every `name#` and `name>` prompt, e.g. of FRR, NETCONF servers and
    unknown devices, which then ran with ISAM's prompt pattern; now it claims only
    ISAM's `name>#` prompts. Its error patterns are used now; a typo had disabled
    them.
  - `ericsson_ban` and `sp_vxoa` claimed every "Last login" line, so logins to Linux
    hosts with a `$` prompt timed out. Their banner checks stay.
  - `junos` claimed every `router1 login:` prompt, e.g. of Linux and BusyBox Telnet
    logins; now only after the `(ttyp0)` line that Junos prints before `login:`.
  - `shell` is also recognized by prompts like `router1:~$ ` or
    `admin@router1:/etc# `.

  Devices whose banner has no vendor signature, e.g. some EOS, ADTRAN and RiOS
  devices, are now guessed as `unknown` (generic driver) instead of a wrong driver.
  The CI job "OS-guess accuracy" reports the accuracy per OS
  (`tools/osguess_report.py`). Pass `driver=` if a device needs a specific driver.

- **BREAKING - Graceful Logout:** `Protocol.close(force=False)` now calls the driver's
  new `logout()` method before the connection is closed. The base `Driver` sends
  `exit\r`, the custom `VRPDriver` sends `quit\r` and `SROSDriver` sends `logout\r`.
  Additional custom drivers may override `Driver.logout(conn)` to implement a
  device-specific logout sequence. The `Netconf` and `Dummy` adapters do not use the
  driver, they rely on a static logout sequence instead (a `<close-session/>` RPC
  respectively a no-op).

  This may be only breaking for the Python API, templates did not need explicit logouts
  before this. Note that the remote host must have left any submode (e.g. config mode,
  local shell) before the connection is closed gracefully, otherwise the logout command
  may fail.

- **Junos Root Shell:** The `junos` driver recognizes the prompt of the shell that
  root gets, e.g. `root@router:~ # ` (csh) or `root@router:/var/tmp # `; before, a
  login as root waited until the timeout. Thanks to yoleri (pull request #211), whose
  banner is now part of the test corpus.
- **NX-OS Banners:** The `nxos` driver also recognizes the banner "Cisco NX-OS
  Software" of newer versions, e.g. nx-osv9000 (upstream issue #200).
- **Login Errors of `ericsson_ban`:** A login over the `ericsson_ban` driver no longer
  fails with `AttributeError: 'str' object has no attribute 'search'`; its login
  error pattern was a string instead of a compiled pattern. A test checks the
  patterns of all drivers.
- **`disable_driver()`:** `Exscript.protocols.drivers.disable_driver()` works; it
  raised a `TypeError` after it had removed the driver only from `driver_map`, so the
  OS guesser still chose it.

#### Class `Exscript.protocols.drivers.Driver`

| Old | New                                  | Comment                                                        |
| --- | ---                                  | ---                                                            |
| -   | `netconf_device_params`              | Passed to ncclient's device handler.                           |
| -   | `netconf_capabilities_re`            | NETCONF capability driver detection pattern.                   |
| -   | `netconf_prompt_re`                  | Response framing with EOM (`]]>]]>`) / EOC (`\n##\n`) pattern. |
| -   | `netconf_error_re`                   | RPC error matching with `<rpc-error>` pattern.                 |
| -   | `__repr__()`                         | Returns a readable `DriverClass('name')` string.               |
| -   | `check_netconf_capabilities(string)` | Checks configured server-capability patterns.                  |

### Class `Exscript.protocols.Protocol`

| Old                                      | New                                                       | Comment                                                                                                               |
| ---                                      | ---                                                       | ---                                                                                                                   |
| -                                        | `cleanup_response(response, ...)`                         | Static method to cleanup a response. Used by the `get_response` method.                                               |
| `close(force=False, reconnecting=False)` | `close(force=False)`                                      | **BREAKING:** `reconnecting` removed. `force=False` now performs a graceful, driver-driven logout before closing.     |
| -                                        | `get_response(*, strip_command, strip_chars, strip_ansi)` | Should be the first choice to retrieve a clean response. `Protocol.response` still exists with the raw received data. |

## Emulators

- **BREAKING - Password Not Echoed:** `VirtualDevice`, which the `Dummy` protocol and
  the test servers use, no longer echoes the password, like real devices. The log and
  `response` of a login to it no longer contain the password; `response` after the
  login is empty instead of the password.

### Class `Exscript.emulators.CommandSet`

| Old                      | New                                             | Comment                                                                                                    |
| ---                      | ---                                             | ---                                                                                                        |
| `add(command, response)` | `add(command, handler, handler_decorator=None)` | **BREAKING:** `response` renamed to `handler` for keyword callers; optional decorator added.               |
| Raises `Exception`       | Raises `ValueError`                             | More specific exception from `add_from_file()` and strict `eval()` calls on missing/non-iterable commands. |

### Class `Exscript.emulators.VirtualDevice`

| Old                                            | New                                        | Comment                                                                 |
| ---                                            | ---                                        | ---                                                                     |
| `add_commands_from_file(..., autoprompt=True)` | `add_commands_from_file(..., prompt=True)` | **BREAKING:** Keyword renamed; callers using `autoprompt=` must update. |

## Template Engine

- **BREAKING - Last Line Without a Line Break:** A template also sends its last line
  if the line does not end with a line break, e.g. `show version` in
  `template.eval(conn, 'ls\nshow version')`. Before, such a line was ignored.
- **BREAKING - Escape Sequences Out of Range:** A Unicode sequence above U+10FFFF,
  such as `\UFFFFFFFF`, and an octal sequence above `\377`, such as `\400`, in a
  command or a string raise a `CompileError` that shows their position. Before, the
  former raised a `SyntaxError` of Python, and the latter gave the characters U+0100
  to U+01FF with a `SyntaxWarning` of Python.
- **BREAKING - `extract` Requires a Regular Expression:** `extract` raises a
  `CompileError` if no regular expression between slashes follows, e.g. in
  `{extract "(a)" as y from "a"}` or `{extract x as y}`. Before, the character after
  `extract` was taken as the delimiter of the regular expression, so a string in
  double quotes worked, and other terms caused confusing errors such as `re.error`.
- **BREAKING - Variables of the Caller Keep Their Values:** A variable that the caller
  passes to a template keeps its value until a statement of the template changes it
  when the template runs. Before, every assignment, `append`, `extract` and `loop`
  statement reset its variables when the template was compiled, even if it never ran:
  with `x='hi'`, `show $x\n{x = "new"}` sent `show None`, `{append "b" to x}` with
  `x=['a']` gave `['b']`, and `extract ... into x` did not append to the list of the
  caller.
- **BREAKING - Operators of the Same Priority:** Operators of the same priority are
  evaluated from left to right: `10 - 2 - 3` is 5, `100 / 10 * 2` is 20, and
  `0 and 1 or 1` is 1. Before, they were evaluated from right to left, so these
  expressions gave 11, 5 and 0, and `20 / 4 / 5` failed with a `ZeroDivisionError`.
  As documented, `and` and `or` have the same priority, so `1 or 0 and 0` is 0. `%`,
  which the documentation did not list, has the priority of `*` and `/`.
- **BREAKING - `and` and `or` Evaluate the Right Operand Only If Needed:** As
  documented, `and` does not evaluate its right operand if the left one is false, and
  `or` not if the left one is true; e.g. `{x = 0 and list.get(list.new(), 1)}` sets `x`
  to 0. Before, both operands were always evaluated, so the right one could raise an
  error or call a function, e.g. one that sends a command.
- **`is not` and `not in` With Several Blanks:** `is  not` and `not  in` with more
  than one blank or a line break between the words mean the same as `is not` and
  `not in`. Before, they gave `None`, and as a condition a `TypeError` of Python.
- **BREAKING - Lines With Only Whitespace:** A line with only whitespace is ignored,
  also if the whitespace is not a space or a tab, e.g. a no-break space. Before, such
  whitespace was sent at the start of the command in the next line.
- **BREAKING - Escaped Characters Start No Comment:** An escaped hash, or a hash
  behind an escaped character, is part of the command: `\# x` sends `# x`,
  `show \}# x` sends `show }# x`, and `show a\n# b` sends `# b` in its second line.
  Before, the hash started a comment there, so `\# x` sent an empty line, and
  `show \}# x` took the next line into the command. A hash behind an `<rpc>` element
  is part of the command as well; before, it sent an empty line.
- **Errors at Runtime:** A division by zero (`1 / 0`, `1 % 0`), an operand of `/`,
  `ge`, `gt`, `le` or `lt` that is not a number (`"a" / 2`), an operand of an
  arithmetic operator without a value, such as a group that `extract` did not match,
  and a bound of `loop from ... to ...` that is not a number raise an `ExecuteError`
  that shows their position. Before, they raised a `ZeroDivisionError`, `ValueError`
  or `TypeError` of Python. Other such exceptions are gone: an empty list is false as
  the condition of `if`, `fail` and `loop`, and as the operand of `not`, and `fail`
  with an empty list has an empty message (before: `IndexError`); `extract ... from`
  matches numbers as text, as `matches` does, e.g. in `{extract /(\d)/ as d from 42}`
  (before: `TypeError`); and the bounds of `loop from ... to ...` may be strings of
  digits, like the operands of arithmetic operators.
- **BREAKING - Values That Are Not Lists:** Operators and statements use a value
  that is not a list like a list: a tuple as a list, and any other value, e.g. the
  `True` that a function returns without a result, a string or a dict from the
  caller, or the connection, as a list with this one item; a function raises an
  `ExecuteError`, as in a string. Before, such values raised an `UnboundLocalError`
  or a `TypeError`, except that `in`, `fail`, `loop` and `extract` used the
  characters of a string, and `in` and `extract` the keys of a dict, e.g.
  `"err" in out()` was a substring test if the function `out` returned a string.
- **Regular Expressions as Operands and Values:** A regular expression that is not
  the right operand of `matches`, e.g. in `/a/ matches /a/`, `/a/ . "b"`,
  `"a" is /a/` or `not /a/`, raises an `ExecuteError` that shows its position, also
  as the condition of `if`, `fail` or `loop`, as a bound or the list of `loop`, as
  the source of `extract`, as the value of `append` and as the message of `fail`.
  Before, it raised an `UnboundLocalError` or a `TypeError` of Python. Assignments
  and functions still take regular expressions.
- **Error Positions in Commands and Strings:** An error about a variable in a command,
  a string or a regular expression points to the variable also behind escape
  sequences, e.g. to `$nothing` in `show \x41 $nothing`, and in a command right before
  a code block or an `<rpc>` element, e.g. in `show $nothing{x = 1}`. Before, it
  pointed too far to the left, in the latter case often to an earlier line.
- **BREAKING - Functions in Strings:** A command or a string that refers to a
  function like to a variable, e.g. `"$f"` with a function `f` that the caller
  passes, raises an `ExecuteError`, as the interpreter intends. Before, it contained
  the text of the function object, such as `<function f at 0x7f...>`.
- **Syntax Errors of Custom Grammars:** If no expression of the grammar of
  `Exscript.parselib.Lexer` matches, and the next 50 characters contain no blank and
  not the end of the input, the lexer raises a `CompileError` that shows these 50
  characters. Before, it raised an `AttributeError`. The grammars of the template
  language were not affected.
- **BREAKING - Errors of the Device in Functions:** If a function of a template raises
  a `ProtocolException`, e.g. `connection.execline()` an `InvalidCommandException` for
  a command that the device rejects, the exception stops the template unchanged, like
  the error of a command, and `try` ignores it. Other exceptions of functions raise an
  `ExecuteError` that shows the position of the call. Before, all of them raised an
  `ExecuteError`, which `try` does not ignore; Exscript 2.6 raised all of them
  unchanged.

### Standard Library

The names below refer to functions callable from templates, not protocol methods.

| Old                                          | New                                          | Comment                                                                                                                                                            |
| ---                                          | ---                                          | ---                                                                                                                                                                |
| `__response__`                               | `__response__`                               | **BREAKING:** Connection helpers now clean responses using `get_response()`, stripping command echoes where applicable, control/ANSI codes, and normalizing CR/LF. |
| -                                            | `connection.get_protocol()`                  | Returns the protocol name, e.g. `ssh`, `telnet`, or `netconf`.                                                                                                     |
| -                                            | `connection.expect(prompt)`                  | Consumes the response and matched prompt.                                                                                                                          |
| `connection.wait_for(prompt)`                | `connection.wait_for(prompt)`                | **BREAKING:** No longer consumes the response/prompt. Use `connection.expect()` for the previous behavior.                                                         |
| `connection.execline()`                      | `connection.execline()`                      | Uses `send()` and `expect_prompt()`; custom protocol `execute()` overrides are no longer called.                                                                   |
| `connection.send()`, `connection.sendline()` | `connection.send()`, `connection.sendline()` | **BREAKING:** Clear the previous `__response__` after sending rather than leaving stale data.                                                                      |
| `connection.close()`                         | `connection.close(force=False)`              | **BREAKING:** Graceful logout by default instead of forced closure; pass `true` in templates to skip logout.                                                       |
| `list.new()`                                 | `list.new(...)`                              | Accepts optional initial values.                                                                                                                                   |
| -                                            | `list.sort(source)`                          | Returns an ascending sorted copy without modifying the source.                                                                                                     |
| -                                            | `list.reverse(source)`                       | Returns a reversed copy without modifying the source.                                                                                                              |
| -                                            | `string.strip(strings, ...)`                 | Removes leading/trailing whitespace or specified characters.                                                                                                       |
| `sys.exec()`                                 | `sys.exec()`                                 | **BREAKING:** Local command output is now text rather than bytes, decoded using Python's default subprocess encoding; line endings are retained.                   |

## Utilities

- **`Exscript.util.syslog.netlog()`:** Works again; on Python 3 it always raised a
  `TypeError`. It also works over IPv6, and the module can be imported on Windows,
  which has no `syslog` module.
- **`Exscript.util.interact.get_filename()`:** Rejects names of files that do not
  exist and asks again, as documented. It passed its check and history one
  position too early to `prompt()`, so it never checked the name, and failed with
  a `TypeError` when a history was given.
- **`Exscript.util.interact.prompt()` Without a Default:** Without a default value
  and a value in the history, or with an empty one, `prompt()` and `get_filename()`
  offer no default, as in `Host: `, and an empty input to `prompt()` returns an empty
  string. Before, they showed an empty value as `Host []: `, and without one offered the
  string `'None'`, as in `Host [None]: `, which `prompt()` returned and stored for an
  empty input.
- **`Exscript.util.interact.get_user()` Without a User Name:** If the name of the
  current user is unknown, e.g. in a container that runs as a user ID without a
  passwd entry and without the `USER` and `LOGNAME` variables, `get_user()`,
  `get_login()` and `read_login()` ask for the user name without offering a default.
  Before, they failed with an `OSError` on Python 3.13 and newer, where
  `getpass.getuser()` raises it instead of a `KeyError`.
- **`exscript` CLI Without a User Name:** Without the login prompt, i.e. with
  `--non-interactive` or `--account-pool`, `--ssh-key` adds an account with the key
  for the current user. If the name of the current user is unknown, it adds none, as
  without a default user name. Before, the CLI failed with the `OSError` of
  `getpass.getuser()`, or with a `KeyError` before Python 3.13.
- **`Exscript.util.mail.send()`:** Ends the SMTP session with `QUIT` and closes the
  connection, also if sending fails; before, it left the connection open. It connects
  only after the mail and its attachments are ready.
- **`Exscript.util.mail` Without a User Name:** If `getpass.getuser()` finds no name
  for the current user, the template variable `user` is empty, so
  `from_template_string()` and `from_template()` work if the template has a `From:`
  line. `Mail()` without a sender, and a template without a `From:` line, raise a
  `ValueError`. Before, all of them failed with the `OSError` of `getuser()`, or with
  a `KeyError` before Python 3.13.
- **Pseudo Protocol on Windows:** `pseudo://` URLs accept absolute Windows paths such
  as `pseudo://C:\devices\router.py`; the drive letter was taken for a port number.
- **`Exscript.util.tty.get_terminal_size()`:** Uses `shutil.get_terminal_size()`: the
  `LINES` and `COLUMNS` environment variables, then the terminal of the standard
  output, then the defaults. It no longer asks standard input, standard error and the
  controlling terminal, and no longer runs `stty size`, which leaked a pipe.
- **`Exscript.util.collections.OrderedDefaultDict`:** Can be deep-copied and pickled,
  and the copies keep the default factory and the order of the keys. Before,
  `copy.deepcopy()` failed with `TypeError: cannot pickle 'odict_items' object`, and
  `pickle.dumps()` with a `PicklingError`.
- **BREAKING - Removed Modules:** `Exscript.util.daemonize`, `Exscript.util.pidutil`
  and `Exscript.util.sigintcatcher` are removed, and
  `daemonize()` failed on Python 3 with `ValueError: can't have unbuffered text I/O`.
  Run long-lived scripts under a service manager such as systemd instead.

## Multi-Threading

## Demos

- Updated the demo scripts to match the latest Exscript version.

## Test Suite

### Test Servers

- **BREAKING - Threaded Servers:** The `Server` base class and its `SSHd`/`Telnetd`
  implementations now run as daemon threads rather than processes. Process-specific
  APIs are no longer available; use `exit()` and `join()` for shutdown.
- **BREAKING - `HTTPd` Removed:** `Exscript.servers.HTTPd` and
  `Exscript.servers.httpd.RequestHandler` are removed. Their HTTP digest
  authentication never worked on Python 3: every login with a valid password failed
  with a `TypeError`. Use `http.server` from the
  standard library or a web framework instead.
- **Client Handling:** `SSHd` and `Telnetd` keep listening after a client disconnects,
  allowing sequential connections. They share the supplied emulator device; concurrent
  clients are not supported.
- **Listening in `start()`:** `start()` of `SSHd` and `Telnetd` listens before it
  returns, so clients can connect at once, and raises errors such as a port in use to
  the caller. Before, the thread bound the port a moment later. Port 0 chooses a free
  port, which the `port` attribute has after `start()`.
