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
  if the logout fails, and raises the error of the logout afterwards. Errors while
  closing, e.g. because the host closed the connection first, are only logged;
  before, `close(force=True)` could raise an `EOFError`.

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
  reply in 4 KiB chunks takes 0.013 seconds instead of 5.2.
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
- **Unicode Escape Sequences Above U+10FFFF:** A sequence such as `\UFFFFFFFF` in a
  command or a string raises a `CompileError` that shows its position. Before, it
  raised a `SyntaxError` of Python.
- **BREAKING - `extract` Requires a Regular Expression:** `extract` raises a
  `CompileError` if no regular expression between slashes follows, e.g. in
  `{extract "(a)" as y from "a"}` or `{extract x as y}`. Before, the character after
  `extract` was taken as the delimiter of the regular expression, so a string in
  double quotes worked, and other terms caused confusing errors such as `re.error`.

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
- **`Exscript.util.mail.send()`:** Ends the SMTP session with `QUIT` and closes the
  connection, also if sending fails; before, it left the connection open. It connects
  only after the mail and its attachments are ready.
- **Pseudo Protocol on Windows:** `pseudo://` URLs accept absolute Windows paths such
  as `pseudo://C:\devices\router.py`; the drive letter was taken for a port number.
- **`Exscript.util.tty.get_terminal_size()`:** Uses `shutil.get_terminal_size()`: the
  `LINES` and `COLUMNS` environment variables, then the terminal of the standard
  output, then the defaults. It no longer asks standard input, standard error and the
  controlling terminal, and no longer runs `stty size`, which leaked a pipe.
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
