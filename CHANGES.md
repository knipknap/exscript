# Changelog

## 3.0.0 (unreleased)

Work in progress: the entries below cover the changes merged from the 2.9 development
line and are completed against Exscript 2.6.32 before the release. Breaking changes are
marked with **BREAKING**; a migration guide will accompany the release.

## General

- **License Labels:** Exscript remains MIT-licensed. `Exscript.protocols.telnetlib` is
  derived from CPython's telnetlib (3.12), so it carries the PSF notice, the license text is
  in `LICENSES/PSF-2.0.txt`, and the package declares `MIT AND PSF-2.0`.
- **Python 2.7 Support:**
- **Python 3.11+ Support:**
- **Dependencies:**
- **NETCONF Protocol:**
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
  `read_eager()`, `read_very_eager()`, `read_lazy()`, `read_very_lazy()`, `interact()`
  and `mt_interact()` with their helpers, `sock_avail()`, `get_socket()`, `fileno()`
  and `set_receive_callback()`; the function `test()`; the option constants other
  than those Exscript negotiates; and the `stdout` and `stderr` arguments. The
  remaining constants are integers instead of bytes, and the options of the
  constructor are keyword-only. Use `Exscript.protocols.Telnet`. If you need a drop-in
  replacement for the telnetlib module that Python 3.13 removed, use the package
  `standard-telnetlib`.

### Protocol Drivers

- **Generic Prompt Pattern in Linear Time:** The prompt pattern of the generic driver,
  which other drivers inherit, backtracked catastrophically on long lines that are no
  prompt: a line with a run of 100 word characters took 1.3 seconds to check, 200
  characters 25 seconds, so hex or base64 output could stall a session. The pattern
  matches the same strings, verified against the old one, in linear time. A test
  checks every driver pattern for this.

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
- **Pseudo Protocol on Windows:** `pseudo://` URLs accept absolute Windows paths such
  as `pseudo://C:\devices\router.py`; the drive letter was taken for a port number.

## Multi-Threading

## Demos

- Updated the demo scripts to match the latest Exscript version.

## Test Suite

### Test Servers

- **BREAKING - Threaded Servers:** The `Server` base class and its `SSHd`/`Telnetd`
  implementations now run as daemon threads rather than processes. Process-specific
  APIs are no longer available; use `exit()` and `join()` for shutdown. `HTTPd` is
  unaffected by this change.
- **Client Handling:** `SSHd` and `Telnetd` keep listening after a client disconnects,
  allowing sequential connections. They share the supplied emulator device; concurrent
  clients are not supported.
