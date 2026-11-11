import unittest

import Exscript.util.crypt


class cryptTest(unittest.TestCase):
    CORRELATE = Exscript.util.crypt

    def testOtp(self):
        from Exscript.util.crypt import otp

        hash = otp('password', 'abc123', 9999)
        self.assertEqual('ACTA AMMO CAR WEB BIN YAP', hash)
        hash = otp('password', 'abc123', 9998)
        self.assertEqual('LESS CLUE LISA MEAT MAGI USER', hash)
        hash = otp('pass', 'abc123', 9998)
        self.assertEqual('DRAB LEER VOTE RICH NEWS FRAU', hash)
        hash = otp('pass', 'abc888', 9998)
        self.assertEqual('DEBT BOON ASKS ORAL MEN WEE', hash)

    def testOtpWithInvalidArguments(self):
        # RFC 2289: a passphrase of 4 to 63 characters, an alphanumeric seed
        # of 1 to 16 characters, and a sequence number that is not negative.
        from Exscript.util.crypt import otp

        for args, error in (
            (('abc', 'abc123', 99), 'passphrase length'),
            (('x' * 64, 'abc123', 99), 'passphrase length'),
            (('password', '', 99), 'seed length'),
            (('password', 'a' * 17, 99), 'seed length'),
            (('password', 'abc 123', 99), 'seed composition'),
            (('password', 'abc123', -1), 'sequence'),
        ):
            with self.subTest(args=args):
                self.assertRaisesRegex(ValueError, '^%s$' % error, otp, *args)
        self.assertEqual(len(otp('x' * 63, 'A' * 16, 0).split()), 6)


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(cryptTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
