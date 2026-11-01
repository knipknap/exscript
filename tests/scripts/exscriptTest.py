import importlib.machinery
import importlib.util
import os
import unittest
from unittest import mock

SCRIPT = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'scripts', 'exscript')


def load_cli():
    loader = importlib.machinery.SourceFileLoader('exscript_cli', SCRIPT)
    spec = importlib.util.spec_from_file_location('exscript_cli', SCRIPT, loader=loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class exscriptTest(unittest.TestCase):
    cli = load_cli()

    def testDuration(self):
        duration = self.cli.duration
        self.assertEqual(duration(''), 0)
        self.assertEqual(duration('90'), 90)
        self.assertEqual(duration('1.5m'), 90)
        self.assertEqual(duration('1h 30m'), 5400)
        self.assertEqual(duration('2d'), 172800)
        for invalid in 'tomorrow', '1x', '-1', '1; rm -rf ~':
            self.assertRaises(ValueError, duration, invalid)

    def testPromptValuesAreLiteralsOnly(self):
        cases = {
            '[1, 2]': [1, 2],
            '42': 42,
            'plain text': 'plain text',
            '__import__("os").getcwd()': '__import__("os").getcwd()',
        }
        for typed, expected in cases.items():
            with mock.patch('builtins.input', return_value=typed):
                self.assertEqual(self.cli.expand_bracket('count', '{#count}'), expected)
