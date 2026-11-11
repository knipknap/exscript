import unittest

from interpreter.helpers import TemplateTestCase

import Exscript.stdlib.crypt


class cryptTest(TemplateTestCase):
    """
    The cryptographic functions of the template language.
    """

    CORRELATE = Exscript.stdlib.crypt

    def testOtp(self):
        variables = self.evaluate(
            '{a = crypt.otp("password", "abc123", 9999)}'
            '{b = crypt.otp("password", "abc123", "9999")}'
            '{c = crypt.otp("password", "abc123", list.new(9999, 9998))}'
        )
        self.assertEqual(variables['a'], ['ACTA AMMO CAR WEB BIN YAP'])
        self.assertEqual(variables['b'], ['ACTA AMMO CAR WEB BIN YAP'])
        self.assertEqual(
            variables['c'], ['ACTA AMMO CAR WEB BIN YAP', 'LESS CLUE LISA MEAT MAGI USER']
        )


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(cryptTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
