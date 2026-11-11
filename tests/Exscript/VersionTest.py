import importlib
import importlib.metadata
import unittest
from unittest import mock

import Exscript
import Exscript.version


class VersionTest(unittest.TestCase):
    CORRELATE = Exscript.version

    def testInstalled(self):
        try:
            installed = importlib.metadata.version('Exscript')
        except importlib.metadata.PackageNotFoundError:
            self.skipTest('Exscript is not installed')
        self.assertEqual(Exscript.version.__version__, installed)
        self.assertEqual(Exscript.__version__, installed)

    def testSourceTreeWithoutInstallation(self):
        self.addCleanup(importlib.reload, Exscript.version)
        error = importlib.metadata.PackageNotFoundError('Exscript')
        with mock.patch('importlib.metadata.version', side_effect=error):
            importlib.reload(Exscript.version)
        self.assertEqual(Exscript.version.__version__, 'DEVELOPMENT')


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(VersionTest)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
