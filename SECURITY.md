# Security Policy

## Supported Versions

Security fixes are made for the latest release of Exscript.

## Reporting a Vulnerability

Please report vulnerabilities privately: open the
[Security tab](https://github.com/knipknap/exscript/security) of the repository and
choose "Report a vulnerability". Do not open a public issue or pull request.

Please include the affected version, a description of the problem, and if possible
the steps or a script to reproduce it. Remove passwords, host names and other data of
your network from logs and recordings first.

The maintainers confirm the report, keep you informed about the fix, and credit you
in the release notes unless you prefer otherwise.

## Security Defaults

- SSH host keys are verified against known_hosts before any credentials are sent;
  unknown hosts are rejected by default (`host_key_policy`).
- Templates run in secure mode by default: they cannot run local commands or access
  local files unless `secure=False` (CLI: `--insecure`) is given.
- XML is parsed without resolving entities, loading DTDs, or accessing the network.
- Passwords are not logged, and the OpenTelemetry instrumentation records commands
  and responses only with `capture_payload=True`.
