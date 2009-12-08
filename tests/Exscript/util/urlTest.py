import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

import Exscript.util.url

urls = [
    ('testhost',
     'telnet://testhost:23'),
    ('testhost?myvar=testvalue',
     'telnet://testhost:23?myvar=testvalue'),
    ('user@testhost',
     'telnet://user@testhost:23'),
    ('user@testhost?myvar=testvalue',
     'telnet://user@testhost:23?myvar=testvalue'),
    ('user:mypass@testhost',
     'user://mypass@testhost'),
    ('user:mypass@testhost?myvar=testvalue',
     'user://mypass@testhost?myvar=testvalue'),
    ('ssh:testhost',
     'ssh://testhost:22'),
    ('ssh:testhost?myvar=testvalue',
     'ssh://testhost:22?myvar=testvalue'),
    ('ssh://testhost',
     'ssh://testhost:22'),
    ('ssh://testhost?myvar=testvalue',
     'ssh://testhost:22?myvar=testvalue'),
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
    ('ssh://user:password@testhost?myvar=testvalue&myvar2=test%202',
     'ssh://user:password@testhost:22?myvar=testvalue&myvar2=test+2'),
    ('ssh://user:password@testhost?myvar=testvalue&amp;myvar2=test%202',
     'ssh://user:password@testhost:22?myvar=testvalue&myvar2=test+2')
]

class urlTest(unittest.TestCase):
    CORRELATE = Exscript.util.url

    def testParseUrl(self):
        from Exscript.util.url import parse_url, Url

        for url, expected in urls:
            result = parse_url(url)
            error  = 'URL:      ' + url + '\n'
            error += 'Result:   ' + str(result) + '\n'
            error += 'Expected: ' + expected
            self.assert_(isinstance(result, Url))
            self.assert_(str(result) == expected, error)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(urlTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
