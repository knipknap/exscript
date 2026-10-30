"""
Golden-file test for the OS guesser.

Replays every banner of the corpus (``banners/``) through the guesser like a
session: protocol info first, the banner during authentication (one character
per read, the worst case), then generic command output and the last banner
line after authentication in different read sizes. The guessed OS and
confidence of every replay are compared with ``osguess-baseline.json``, so any
change of the guessing behavior shows up as a reviewable diff.

After an intended change, regenerate the file with ``EXSCRIPT_UPDATE_GOLDEN=1``
and review the diff.
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from Exscript.protocols.osguesser import OsGuesser

DIRNAME = os.path.dirname(os.path.abspath(__file__))
BANNER_DIR = os.path.join(DIRNAME, 'banners')
GOLDEN = os.path.join(DIRNAME, 'osguess-baseline.json')
PROTOCOL_INFOS = ['', 'SSH-2.0-Cisco-1.25', 'SSH-2.0-OpenSSH_9.6']
READ_SIZES = [64, 65536]
GENERIC_OUTPUT = '\r\n'.join(
    ['interface GigabitEthernet0/%d\r\n description uplink #%d to core\r\n'
     ' ip address 10.0.%d.1 255.255.255.0\r\n!' % (i, i, i) for i in range(40)]
    + ['# end of config', 'Building configuration...', 'Current configuration : 8231 bytes']
)
PROMPT_ONLY = ['router#', 'switch>', 'RP/0/RSP0/CPU0:xr-pe1#', 'user@host:~$', 'root@host:~#',
               '<HUAWEI>', 'A:sros-pe1#', '[admin@MikroTik] >', 'FGT60E #', 'core-sw01(config)#',
               'admin@junos-mx> ']


def feed(guesser, data, authenticated, size):
    for i in range(0, len(data), size):
        guesser.check_received_data(data[i:i + size], authenticated)


def snapshot(guesser):
    return (dict(guesser._info), guesser._auth_buffer,
            guesser._protocol_buffer, guesser._response_buffer)


def restore(state):
    guesser = OsGuesser()
    (guesser._info, guesser._auth_buffer,
     guesser._protocol_buffer, guesser._response_buffer) = dict(state[0]), *state[1:]
    return guesser


def replay(name, auth_data, protocol_info, after_auth, results):
    """Runs the auth phase once, then the post-auth phase for every read size."""
    guesser = OsGuesser()
    guesser.check_protocol_info(protocol_info)
    feed(guesser, auth_data, False, 1)
    state = snapshot(guesser)
    for size in READ_SIZES:
        guesser = restore(state)
        feed(guesser, after_auth, True, size)
        results['%s|%s|%d' % (name, protocol_info or '-', size)] = {
            'after_auth': list(state[0]['os']),
            'final': list(guesser._info['os']),
        }


def run_corpus():
    results = {}
    for name in sorted(os.listdir(BANNER_DIR)):
        if name.startswith('.'):
            continue
        with open(os.path.join(BANNER_DIR, name), encoding='utf-8') as fp:
            banner = fp.read().rstrip('\n')
        last_line = banner.replace('\r', '\n').rstrip('\n').split('\n')[-1]
        for info in PROTOCOL_INFOS:
            replay(name, banner, info, '\r\n' + GENERIC_OUTPUT + '\r\n' + last_line, results)
    for prompt in PROMPT_ONLY:
        replay('prompt-only:' + prompt, 'Last login: Mon Oct 26 10:00:00 2026\r\n',
               'SSH-2.0-OpenSSH_9.6', '\r\n' + GENERIC_OUTPUT + '\r\n' + prompt, results)
    return results


class OsGuesserCorpusTest(unittest.TestCase):

    def testCorpusMatchesBaseline(self):
        results = run_corpus()
        if os.environ.get('EXSCRIPT_UPDATE_GOLDEN'):
            with open(GOLDEN, 'w', encoding='utf-8', newline='\n') as fp:
                json.dump(results, fp, indent=1, sort_keys=True)
                fp.write('\n')
            self.skipTest('golden file regenerated: ' + GOLDEN)
        with open(GOLDEN, encoding='utf-8') as fp:
            expected = json.load(fp)
        changed = sorted(key for key in expected.keys() | results.keys()
                         if expected.get(key) != results.get(key))
        details = ['%s: %s -> %s' % (key, expected.get(key), results.get(key)) for key in changed[:20]]
        self.assertEqual(changed, [], 'OS guessing changed:\n' + '\n'.join(details))


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(OsGuesserCorpusTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
