import unittest

from Exscript import stdlib
from Exscript.stdlib import connection, crypt, file, ipv4, mysys, string
from Exscript.stdlib import list as list_functions

# The functions that run local commands or access local files.
INSECURE = {
    'file.chmod',
    'file.clear',
    'file.mkdir',
    'file.read',
    'file.rm',
    'file.write',
    'sys.env',
    'sys.exec',
}


class functionsTest(unittest.TestCase):
    """
    The table of the functions of the template language.
    """

    def testNames(self):
        modules = {
            'connection': connection,
            'crypt': crypt,
            'file': file,
            'ipv4': ipv4,
            'list': list_functions,
            'string': string,
            'sys': mysys,
        }
        renamed = {'connection.exec': 'exec_', 'sys.exec': 'execute'}
        for name, function in stdlib.functions.items():
            with self.subTest(name=name):
                prefix, attribute = name.split('.')
                attribute = renamed.get(name, attribute)
                self.assertIs(function, getattr(modules[prefix], attribute))

    def testInsecureFunctions(self):
        insecure = {name for name, f in stdlib.functions.items() if not hasattr(f, '_is_secure')}
        self.assertEqual(insecure, INSECURE)


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(functionsTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
