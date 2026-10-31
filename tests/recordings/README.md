# Recorded device sessions

`tests/Exscript/protocols/ReplayTest.py` replays every `*/*.jsonl` file in this directory against
the real Telnet, SSH and NETCONF adapters and compares the results with the `.golden.json` file next
to it. The replay server (`tests/Exscript/protocols/replay.py`) runs on 127.0.0.1 and sends the
recorded device output, so the tests need no devices.

Each recording runs twice: with the output as recorded, and split into small random pieces. Both
runs must give the same result. A third test checks the device's ground truth: login succeeds and
`guess_os()` returns `device.os`.

## Adding a recording

1. Write a command file (see `commands/`). For CLI sessions, put one command per line; empty lines
   and lines starting with `#` are skipped. `!secret` sends a second secret that the recorder asks
   for (e.g. after `enable`), and `!send TEXT` sends keys without a line end (`!send \x20` answers a
   pager). For NETCONF, separate the RPC bodies with lines of `---`.

2. Record the session. The recorder asks for the password and never stores it:

   ```sh
   uv run tools/record_session.py ssh 192.0.2.1 -u admin -c cmds.txt -o raw.jsonl \
       --os ios --os-version 15.9 --platform C2960X
   ```

   - The protocol is `ssh`, `telnet` or `netconf`.
   - `--os` is the ground truth: the Exscript driver name that `guess_os()` should return
     (`unknown` if no driver fits).
   - Keep the default terminal type `dumb`. It is Exscript's default, and the replay test uses the
     recorded type.
   - Use `--auth password` for SSH servers that drop the connection after a failed
     keyboard-interactive attempt.
   - See `--help` for the other options.

3. Sanitize the recording, and replace host names, user names and anything else identifying:

   ```sh
   uv run tools/sanitize_recording.py raw.jsonl tests/recordings/ios/ios-15.9-c2960x-ssh.jsonl \
       --replace core-rtr-01=router1 --replace jdoe=admin
   ```

   The sanitizer replaces addresses, MACs, secrets and serial numbers, and prints every replacement
   and the prompts it saw. It cannot know every identifier: read the sanitized file before
   committing it. Never commit a raw recording.

4. Create the golden file, review it, and commit both files:

   ```sh
   EXSCRIPT_UPDATE_GOLDEN=1 uv run pytest tests/Exscript/protocols/ReplayTest.py
   ```

   If Exscript does not handle the device correctly yet, add the recording to `KNOWN_ISSUES` in
   `ReplayTest.py` with the reason. If its results depend on read timing, add it to
   `TIMING_ISSUES` instead.

Name files `<dir>/<os>-<version>-<platform>-<protocol>[-<scenario>].jsonl`. The directory groups
recordings by device family.

## Format (version 1)

A recording is a JSON Lines file. Bytes are stored as strings with one character per byte
(latin-1).

The first line is the header:

```json
{"format": "exscript-recording", "version": 1, "protocol": "ssh", "date": "2026-10-31",
 "sanitized": true, "device": {"os": "shell", "version": "Alpine Linux 3.22", "platform": "docker"},
 "ssh": {"server_version": "SSH-2.0-OpenSSH_10.0", "banner": null,
         "auth_methods": ["publickey", "password", "keyboard-interactive"], "interactive": null,
         "host_key_type": "ssh-ed25519"},
 "terminal": {"type": "dumb", "width": 80, "height": 24}}
```

- `ssh` (SSH and NETCONF only) holds the server's version string, the pre-login banner, the
  authentication methods it offered, and the keyboard-interactive query it sent, if any.
- `terminal` (CLI sessions only) holds the terminal that the recorder requested.
- `incomplete: true` marks a recording that ended with an error.

Each following line is an event:

```json
{"t": 2.1, "dir": "send", "data": "show version\r", "phase": "command"}
{"t": 2.103, "dir": "recv", "data": "show version\r\nCisco IOS Software, ..."}
{"t": 4.073, "dir": "send", "data": "", "secret": true, "phase": "login"}
{"t": 28.161, "dir": "close", "data": ""}
```

- `t` is the time in seconds since the connection was opened.
- `dir` is `recv` (device output), `send` (client input) or `close` (the device closed the
  connection).
- `phase` of a `send` event is `negotiation` (Telnet options), `login`, `command` or `logout`.
- A `send` with `secret: true` is a password whose data was not stored.

For NETCONF, the data is the raw content of the `netconf` SSH subsystem, including the framing.

## Replay rules

- **Matching input.** The server sends the output up to the next recorded `send` and waits for a
  line from the client. A matching line continues the replay. A recorded secret matches any line.
  Any other line is echoed and answered with the last prompt, so `login()` may send commands that
  were not recorded, such as `enable`.
- **Reconnects.** Every connection replays the recording from the start, because some drivers
  reconnect between SSH authentication methods.
- **NETCONF.** An RPC gets the next recorded reply if the operation name matches. The reply gets
  the client's message-id and keeps its recorded chunk sizes. An unrecorded `close-session` gets
  `<ok/>`; any other unrecorded RPC gets an `rpc-error`.
- **Authentication.** The SSH server accepts any password or keyboard-interactive answer.
