#!/usr/bin/env python3
"""
Type coverage: runs mypy with the settings in pyproject.toml and prints the
share of expressions whose type mypy knows, i.e. is not ``Any``, in Markdown.

Every function is annotated (mypy checks strictly). ``Any`` remains where a
type is open on purpose (callbacks, options that are passed on, template
variables) and where an untyped library returns it (ncclient).

With --check, it fails if mypy reports an error or if the coverage is below
MIN_PERCENT, so the coverage only goes up; raise MIN_PERCENT when a change
improves it. Run from the repository root::

    uv run python tools/type_coverage.py [--check]
"""

import argparse
import os
import sys
import tempfile

from mypy import api

MIN_PERCENT = 95.0


def main() -> int:
    """Run mypy, print the coverage, and return the exit status."""
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0].strip())
    parser.add_argument('--check', action='store_true', help=f'fail below {MIN_PERCENT} %%')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as report_dir:
        stdout, stderr, status = api.run(['--any-exprs-report', report_dir])
        sys.stderr.write(stderr)
        if status:
            sys.stdout.write(stdout)
            return status
        with open(os.path.join(report_dir, 'any-exprs.txt'), encoding='utf-8') as file:
            rows = [line.split() for line in file]
    modules = {
        row[0]: (int(row[1]), int(row[2])) for row in rows if len(row) == 4 and row[1].isdigit()
    }
    anys, exprs = modules.pop('Total')
    percent = 100.0 * (exprs - anys) / exprs
    print(
        f'Type coverage: **{percent:.2f} %** of {exprs} expressions have a known type (minimum {MIN_PERCENT} %).'
    )
    low = sorted(
        (100.0 * (e - a) / e, name) for name, (a, e) in modules.items() if e and a / e > 0.1
    )
    if low:
        print('\nBelow 90 %:\n')
        for module_percent, name in low:
            print(f'- {name}: {module_percent:.1f} %')
    return 1 if args.check and percent < MIN_PERCENT else 0


if __name__ == '__main__':
    sys.exit(main())
