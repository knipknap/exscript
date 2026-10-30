# Changelog

## 3.0.0 (unreleased)

Work in progress: the entries below cover the changes merged from the 2.9 development
line and are completed against Exscript 2.6.32 before the release. Breaking changes are
marked with **BREAKING**; a migration guide will accompany the release.

## General

- **Python 2.7 Support:**
- **Python 3.11+ Support:**
- **Dependencies:**
- **NETCONF Protocol:**
- **OpenTelemetry Tracing (optional):** Install the `otel` extra (`Exscript[otel]`)
  and use `Exscript.contrib.otel.ExscriptInstrumentor` to instrument `Protocol` and
  `Netconf` operations. It creates spans for connect, login/authentication, send,
  execute, and close, and records operation durations. Span attributes may include
  host names, usernames, commands, and response contents.

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

### Protocol Drivers

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
