import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from Exscript.util.url import Url

urls = [
    # No protocol.
    ('testhost',
     'telnet://testhost:23'),
    ('testhost?myvar=testvalue',
     'telnet://testhost:23?myvar=testvalue'),

    # No protocol + empty user.
    ('@testhost',
     'telnet://@testhost:23'),
    ('@testhost?myvar=testvalue',
     'telnet://@testhost:23?myvar=testvalue'),

    # No protocol + user.
    ('user@testhost',
     'telnet://user@testhost:23'),
    ('user:password@testhost',
     'telnet://user:password@testhost:23'),
    ('user:password:password2@testhost',
     'telnet://user:password:password2@testhost:23'),

    # No protocol + empty password 1.
    ('user:@testhost',
     'telnet://user:@testhost:23'),
    ('user::password2@testhost',
     'telnet://user::password2@testhost:23'),
    (':@testhost',
     'telnet://:@testhost:23'),

    # No protocol + empty password 2.
    ('user:password:@testhost',
     'telnet://user:password:@testhost:23'),
    ('user::@testhost',
     'telnet://user::@testhost:23'),
    ('::@testhost',
     'telnet://::@testhost:23'),
    (':password:@testhost',
     'telnet://:password:@testhost:23'),

    # Protocol.
    ('ssh1://testhost',
     'ssh1://testhost:22'),
    ('ssh1://testhost?myvar=testvalue',
     'ssh1://testhost:22?myvar=testvalue'),

    # Protocol + empty user.
    ('ssh://@testhost',
     'ssh://@testhost:22'),
    ('ssh://:password@testhost',
     'ssh://:password@testhost:22'),
    ('ssh://:password:password2@testhost',
     'ssh://:password:password2@testhost:22'),

    # Protocol + user.
    ('ssh://user@testhost',
     'ssh://user@testhost:22'),
    ('ssh://user@testhost?myvar=testvalue',
     'ssh://user@testhost:22?myvar=testvalue'),
    ('ssh://user:password@testhost',
     'ssh://user:password@testhost:22'),
    ('ssh://user:password@testhost?myvar=testvalue',
     'ssh://user:password@testhost:22?myvar=testvalue'),
    ('ssh://user:password@testhost',
     'ssh://user:password@testhost:22'),
    ('ssh://user:password:password2@testhost',
     'ssh://user:password:password2@testhost:22'),

    # Multiple arguments.
    ('ssh://user:password@testhost?myvar=testvalue&myvar2=test%202',
     'ssh://user:password@testhost:22?myvar=testvalue&myvar2=test+2'),
    ('ssh://user:password@testhost?myvar=testvalue&amp;myvar2=test%202',
     'ssh://user:password@testhost:22?myvar=testvalue&myvar2=test+2'),

    # Encoding.
    ('foo://%27M%7B7Zk:%27%2FM%7B7Zyk:C7%26Rt%3Ea@ULM-SZRC1:23',
     'foo://%27M%7B7Zk:%27%2FM%7B7Zyk:C7%26Rt%3Ea@ULM-SZRC1:23'),

    # Pseudo protocol.
    ('pseudo://../my/path',
     'pseudo://../my/path'),
    ('pseudo://../path',
     'pseudo://../path'),
    ('pseudo://filename',
     'pseudo://filename'),
    ('pseudo:///abspath',
     'pseudo:///abspath'),
    ('pseudo:///abs/path',
     'pseudo:///abs/path'),
]

class urlTest(unittest.TestCase):
    CORRELATE = Url

    def testConstructor(self):
        self.assert_(isinstance(Url(), Url))

    def testToString(self):
        for url, expected in urls:
            result = Url.from_string(url)
            error  = 'URL:      ' + url + '\n'
            error += 'Result:   ' + str(result) + '\n'
            error += 'Expected: ' + expected
            self.assert_(isinstance(result, Url))
            self.assert_(result.to_string() == expected, error)

    def testFromString(self):
        for url, expected in urls:
            result = Url.from_string(url)
            error  = 'URL:      ' + url + '\n'
            error += 'Result:   ' + str(result) + '\n'
            error += 'Expected: ' + expected
            self.assert_(isinstance(result, Url))
            self.assert_(str(result) == expected, error)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(urlTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
