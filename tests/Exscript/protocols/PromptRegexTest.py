import itertools
import random
import re
import string
import time
import unittest

from Exscript.protocols.drivers import driver_map
from Exscript.protocols.drivers.driver import _prompt_re


def old_generic_prompt():
    """Returns a reference regex: the generic prompt regex must match the same strings."""
    unprintable = r'[^' + re.escape(string.printable) + r']'
    start = r'(?:\r\n|[\r\n])(?:' + unprintable + r'*|[\x1b\x07\x00]*)'
    filename = r'(?:[\w\+\-\._]+)'
    path = r'(?:(?:' + filename + r')?(?:/' + filename + r')*/?)'
    any_path = r'(?:' + path + r'|~' + path + r'?)'
    user_host = r'(?:(?:(?:[\w+\-]+)\@)?(?:[\w+\-\.]+))'
    middle = r'[\[\<]?\w+' + user_host + r'?:?' + any_path + r'?[: ]?' + any_path + r'?'
    end = r'(?:\(' + filename + r'\))?[\]\-]?[#>%\$\]] ?' + unprintable + r'*\Z'
    return re.compile(start + middle + end, re.I)


def span(regex, text):
    match = regex.search(text)
    return match.span() if match else None


# Reference patterns for the Junos and MRV prompts. JUNOS_BEFORE and MRV_BEFORE match
# runs of line breaks with backtracking, which takes exponential time on many line breaks.
_JUNOS_TAGS = (
    r'(?:\{master(?::\d+)?\}|\{backup(?::\d+)?\}|\{primary:node\d+\}|\{secondary:node\d+\})'
)
_JUNOS_PREFIX = r'(?:(?:\r\n|[\r\n])+' + _JUNOS_TAGS + r'?(?:\[edit[^\]\r\n]*\])?)?'
JUNOS_2X = re.compile(_JUNOS_PREFIX + r'(?:\r\n|[\r\n])+[\w\-\.]+@[\-\w+\.:]+[%>#] $')
JUNOS_BEFORE = re.compile(
    _JUNOS_PREFIX + r'(?:\r\n|[\r\n])+[\w\-\.]+@[\-\w+\.:]++(?:[~/][\w\-\./]*+ ?)?[%>#] $'
)
MRV_BEFORE = re.compile(r'(?:\r\n|[\r\n])+[^$\r\n]+\$ ?$')


def random_texts(alphabet, count, seed):
    """Returns random texts that start with a line break, of up to 16 items of the alphabet."""
    rng = random.Random(seed)
    for _ in range(count):
        yield '\r\n' + ''.join(rng.choice(alphabet) for _ in range(rng.randint(0, 16)))


class PromptRegexTest(unittest.TestCase):
    """The prompt regexes of the drivers."""

    def testGenericPromptMatchesTheSameStrings(self):
        old, new = old_generic_prompt(), _prompt_re[0]
        alphabet = list('ab_1é+-.@: ~/()[]<>#%$\r\nß\tX') + ['\x1b', '\x07', '\x00', '\x01']
        rng = random.Random(20261103)
        for _ in range(30000):
            prefix = rng.choice(['', '\r\n', '\n', 'x\r\n', '\r\n\x1b'])
            text = prefix + ''.join(rng.choice(alphabet) for _ in range(rng.randint(0, 18)))
            self.assertEqual(span(old, text), span(new, text), repr(text))
        for length in range(1, 5):
            for chars in itertools.product(list('a.-@:/~ #]([') + ['\r\n'], repeat=length):
                text = '\r\n' + ''.join(chars)
                self.assertEqual(span(old, text), span(new, text), repr(text))

    def testGenericPrompts(self):
        prompts = [
            'router#',
            'router> ',
            'user@host:~$ ',
            'user@host:~/dir/sub$ ',
            '[user@host ~]$ ',
            '<HUAWEI>',
            'RP/0/RSP0/CPU0:router(config)#',
            'router(config-if)#',
            'host%',
        ]
        for prompt in prompts:
            self.assertTrue(_prompt_re[0].search('output\r\n' + prompt), prompt)
        for text in 'a b c#', 'ab.cd@host#', 'a@host#', 'a:b:c:d#', 'line without prompt':
            self.assertIsNone(_prompt_re[0].search('output\r\n' + text), text)

    def testJunosPrompts(self):
        regex = driver_map['junos'].prompt_re[0]
        prompts = [
            'sab@DD-EA3> ',
            'pheller@sw3# ',
            '{master:3}\r\npheller@sw3> ',
            '{primary:node0}[edit interfaces]\r\npheller@fw1# ',
            'root@router% ',
            'root@router:RE:0% ',
            'root@testhost:~ # ',  # csh, the shell of root
            'root@router:/var/tmp # ',
            'root@router:~# ',
        ]
        for prompt in prompts:
            self.assertTrue(regex.search('output\r\n' + prompt), prompt)
        for text in (
            'sab@DD-EA3>',
            'show route | match 10.0.0.1 ',
            'a@b c # ',
            'line without prompt',
        ):
            self.assertIsNone(regex.search('output\r\n' + text), text)

        # The pattern matches everything that JUNOS_2X matches, at the same position.
        alphabet = list('ab_1.-@:~/ #>%{}[]') + ['\r\n']
        for text in random_texts(alphabet, 20000, 20261110):
            if JUNOS_2X.search(text):
                self.assertEqual(span(JUNOS_2X, text), span(regex, text), repr(text))

    def testRunsOfLineBreaksAsBefore(self):
        # The patterns match each run of line breaks as a whole, and the same texts at the
        # same positions as JUNOS_BEFORE and MRV_BEFORE, which backtrack on the runs.
        tokens = [
            '\r\n',
            '\r',
            '\n',
            ' ',
            '$',
            '#',
            '>',
            '%',
            'a',
            'b1',
            '.',
            '-',
            '@',
            ':',
            '~',
            '/',
        ]
        tags = ['{master}', '{backup:1}', '{primary:node0}', '[edit]', '[edit interfaces]']
        for name, before, alphabet in (
            ('junos', JUNOS_BEFORE, tokens + tags),
            ('mrv', MRV_BEFORE, tokens),
        ):
            regex = driver_map[name].prompt_re[0]
            for text in random_texts(alphabet, 30000, 20261111):
                self.assertEqual(span(before, text), span(regex, text), f'{name}: {text!r}')

    def testAllRegexesNeedLinearTime(self):
        # Lines that are no prompt but contain long runs of the characters that
        # prompts consist of. A regex with catastrophic backtracking needs
        # seconds to minutes for them; the others need microseconds.
        lines = [
            'a' * 120 + ' x',
            'a.' * 60 + '!',
            'a-' * 60 + '!',
            '1 ' * 60 + '!',
            'a/' * 60 + '!',
            ('a' * 60 + ' ') * 2 + '!',
            'ab:' * 40 + '!',
            '(a' * 60 + '!',
            'a@' * 60 + '!',
            '\x1b[0m' * 30 + 'a' * 60 + '!',
        ]
        texts = ['\r\n' + line for line in lines] + [' ' * 120 + '!', 'x\r\n' * 1000]
        # Runs of line breaks as long as the window in which prompts are searched.
        texts += ['\r\n' * 512 + '!', '\n' * 1024 + '!', '\r\n' * 400 + '{master}\r\n!']
        for name, driver in driver_map.items():
            for attr, value in vars(driver).items():
                if not isinstance(value, list):
                    continue
                for regex in value:
                    if not isinstance(regex, re.Pattern):
                        continue
                    for text in texts:
                        start = time.perf_counter()
                        regex.search(text)
                        elapsed = time.perf_counter() - start
                        self.assertLess(elapsed, 0.2, f'{name}.{attr} on {text[:30]!r}')
            # The OS guesser runs these on every read until it is sure.
            for check in 'check_protocol_for_os', 'check_head_for_os', 'check_response_for_os':
                for text in texts:
                    start = time.perf_counter()
                    getattr(driver, check)(text)
                    elapsed = time.perf_counter() - start
                    self.assertLess(elapsed, 0.2, f'{name}.{check} on {text[:30]!r}')
