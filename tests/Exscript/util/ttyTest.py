import os
import unittest
from unittest import mock

import Exscript.util.tty
from Exscript.util.tty import get_terminal_size

NO_SIZE_VARIABLES = {'LINES': '', 'COLUMNS': ''}


class ttyTest(unittest.TestCase):
    CORRELATE = Exscript.util.tty

    def testEnvironmentVariables(self):
        with mock.patch.dict(os.environ, {'LINES': '50', 'COLUMNS': '132'}):
            self.assertEqual(get_terminal_size(), (50, 132))

    def testTerminal(self):
        size = os.terminal_size((120, 40))
        with (
            mock.patch.dict(os.environ, NO_SIZE_VARIABLES),
            mock.patch('os.get_terminal_size', return_value=size),
        ):
            self.assertEqual(get_terminal_size(), (40, 120))

    def testDefaults(self):
        with (
            mock.patch.dict(os.environ, NO_SIZE_VARIABLES),
            mock.patch('os.get_terminal_size', side_effect=OSError),
        ):
            self.assertEqual(get_terminal_size(), (25, 80))
            self.assertEqual(get_terminal_size(10, 20), (10, 20))


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(ttyTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
