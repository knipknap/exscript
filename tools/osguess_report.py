#!/usr/bin/env python3
"""
OS-guess accuracy: compares guess_os() with the ground truth, and prints the
result per OS and the wrong guesses in Markdown.

The truth of a banner in tests/Exscript/protocols/banners is its file name
(``ios.3``: ios). Each banner is replayed through the OS guesser like a Telnet
session and like an SSH session whose version string names no vendor, in small
and large reads. The truth of a recording in tests/recordings is ``device.os``
in its header; recordings are replayed against the real adapters.

With --check, it fails if fewer sessions are right than MIN_CORRECT, so the
accuracy only goes up; raise MIN_CORRECT when a change improves it. Run from
the repository root::

    python tools/osguess_report.py [--check]
"""

import argparse
import collections
import glob
import os
import sys

sys.path.insert(0, os.getcwd())  # for the test helpers

from tests.Exscript.protocols import OsGuesserCorpusTest as corpus  # noqa: E402
from tests.Exscript.protocols import ReplayTest as replays  # noqa: E402
from tests.Exscript.protocols.replay import Recording  # noqa: E402

MIN_CORRECT = 217  # 2026-11-10; raise it when a change guesses more sessions right


def banner_sessions():
    """Yields (session, truth, guess) for each banner, protocol and read size."""
    results = {}
    for name in sorted(os.listdir(corpus.BANNER_DIR)):
        if name.startswith('.'):
            continue
        with open(os.path.join(corpus.BANNER_DIR, name), encoding='utf-8') as fp:
            banner = fp.read().rstrip('\n')
        last_line = banner.replace('\r', '\n').rstrip('\n').split('\n')[-1]
        after_auth = '\r\n' + corpus.GENERIC_OUTPUT + '\r\n' + last_line
        for info in '', 'SSH-2.0-OpenSSH_9.6':
            corpus.replay(name, banner, info, after_auth, results)
    for key, result in sorted(results.items()):
        name, info, size = key.split('|')
        protocol = 'Telnet' if info == '-' else 'SSH'
        yield (
            f'banner {name}, {protocol}, {size}-byte reads',
            name.split('.')[0],
            result['final'][0],
        )


def recording_sessions():
    """Yields (session, truth, guess) for each recording with a ground truth."""
    for path in sorted(glob.glob(os.path.join(replays.RECORDINGS, '*', '*.jsonl'))):
        truth = Recording(path).header['device'].get('os')
        if truth:
            name = os.path.relpath(path, replays.RECORDINGS).replace(os.sep, '/')
            yield f'recording {name}', truth, replays.replay(path, 'recorded')[0]['os']


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--check', action='store_true', help='fail below MIN_CORRECT')
    args = parser.parse_args()

    sessions = [*banner_sessions(), *recording_sessions()]
    right = sum(truth == guess for _, truth, guess in sessions)
    per_os = collections.defaultdict(collections.Counter)
    for _, truth, guess in sessions:
        per_os[truth][guess] += 1

    print('### OS-guess accuracy\n')
    print(f'{right} of {len(sessions)} sessions guessed right ({right / len(sessions):.0%}).\n')
    print('| Truth | Sessions | Right | Guessed instead |')
    print('|---|---:|---:|---|')
    for truth, guesses in sorted(per_os.items()):
        instead = ', '.join(f'{os_} ({n})' for os_, n in guesses.most_common() if os_ != truth)
        print(f'| {truth} | {guesses.total()} | {guesses[truth]} | {instead} |')
    wrong = [(session, guess) for session, truth, guess in sessions if truth != guess]
    if wrong:
        print('\n<details><summary>Wrong guesses</summary>\n')
        for session, guess in wrong:
            print(f'- {session}: {guess}')
        print('\n</details>')
    if args.check and right < MIN_CORRECT:
        sys.exit(f'\nFewer sessions guessed right than before: {right} < {MIN_CORRECT}')


if __name__ == '__main__':
    main()
