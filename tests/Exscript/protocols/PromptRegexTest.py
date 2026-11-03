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
