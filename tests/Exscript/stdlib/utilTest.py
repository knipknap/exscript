import unittest

import Exscript.stdlib.util
from Exscript.stdlib.util import secure_function


def concat(scope, *args, separator=''):
    """Joins the arguments."""
    return [separator.join(args)]


class utilTest(unittest.TestCase):
    """
    The decorator that marks functions of the template language as secure.
    """

    CORRELATE = Exscript.stdlib.util

    def testSecureFunction(self):
        wrapper = secure_function(concat)
        self.assertTrue(wrapper._is_secure)
        self.assertFalse(hasattr(concat, '_is_secure'))
        self.assertEqual(wrapper('scope', 'a', 'b', separator='-'), ['a-b'])
        self.assertEqual((wrapper.__name__, wrapper.__doc__), ('concat', 'Joins the arguments.'))
        self.assertIs(wrapper.__wrapped__, concat)


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(utilTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
