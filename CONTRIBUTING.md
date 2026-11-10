# Contributing to Exscript

Thank you for helping! Bug reports, recordings of devices, drivers, fixes and documentation
are all welcome.

## Reporting problems

Open an [issue](https://github.com/knipknap/exscript/issues/new/choose). There is a form for
bugs, and one for devices that get the wrong driver or none. Report vulnerabilities privately,
as described in the [security policy](https://github.com/knipknap/exscript/security/policy).

## Development setup

Exscript uses [uv](https://docs.astral.sh/uv/), which installs Python and all development tools
into `.venv`:

```sh
git clone https://github.com/knipknap/exscript.git
cd exscript
uv sync
uvx pre-commit install
```

## Checks

CI runs these checks on every pull request. Run them before you push:

```sh
uv run pytest                    # the tests; warnings are errors
uv run mypy                      # the type checks
uvx pre-commit run --all-files   # ruff, formatting, and checks of the workflows
uv run --group docs sphinx-build -W --keep-going docs docs/_build/html   # the documentation
```

The tests need no devices and no network: they run against local test servers and replay
recorded sessions. To run them with another Python version, use e.g.
`uv run --python 3.15 pytest`.

CI also measures three kinds of coverage, each with a minimum that only goes up:

- tests: `uv run pytest --cov=Exscript` (lines and branches; the minimum is
  `COV_FAIL_UNDER` in `.github/workflows/ci.yml`),
- docstrings: interrogate in pre-commit (`fail-under` in `pyproject.toml`),
- types: `uv run python tools/type_coverage.py --check`, the share of expressions whose
  type mypy knows (`MIN_PERCENT` in the tool).

## Changes

- A fix comes with a test that fails without it.
- Describe changes that users notice in `CHANGES.md`. Mark breaking changes with
  **BREAKING**, and say how to migrate.
- Document new functions, classes and modules with docstrings in the style of the existing
  code (`:param:`, `:type:`, `:return:`, `:rtype:`). The API reference is generated from
  them, and pre-commit fails if the share of documented functions drops.
- Annotate new code with types. mypy checks every module strictly, except those that are
  still in the list of `[[tool.mypy.overrides]]` in `pyproject.toml`; remove a module from
  that list when you annotate it. Use `Any` only where a type is open on purpose.
- The public API and the template language stay compatible. Please open an issue before you
  work on a change that breaks them.

## Drivers and OS detection

[Writing a driver](https://exscript.readthedocs.io/en/latest/drivers.html#writing-a-driver)
describes the driver class. Add the banner of the device (the text up to the first prompt,
sanitized) as `tests/Exscript/protocols/banners/<driver>.<n>`, then update the expected
guesses and check that the accuracy does not drop:

```sh
EXSCRIPT_UPDATE_GOLDEN=1 uv run pytest tests/Exscript/protocols/OsGuesserCorpusTest.py
uv run python tools/osguess_report.py --check
```

Review the diff of `osguess-baseline.json`: no guess that was right may become wrong. If the
accuracy improves, raise `MIN_CORRECT` in `tools/osguess_report.py`.

## Recordings

Recorded sessions of real devices let the tests cover what devices really send.
[tests/recordings/README.md](https://github.com/knipknap/exscript/blob/master/tests/recordings/README.md)
describes how to record, sanitize and add them. Never commit an unsanitized recording: device
output can contain passwords, addresses, host names and customer data.

## Performance

`uv run python tools/bench_bulk.py` measures the connection layer on loopback. CI fails if a
result exceeds four times its target.

## Releases

Maintainers release from `master`: update `CHANGES.md`, then push a tag such as `v3.0.0` or
`v3.0.0rc1`. The release workflow builds the distributions, publishes them to PyPI, and
creates the GitHub release; tags with `a`, `b` or `rc` become pre-releases.
