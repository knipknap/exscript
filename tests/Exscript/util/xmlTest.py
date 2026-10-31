import os
import pathlib
import tempfile
import unittest

from lxml import etree

from Exscript.util import xml
from Exscript.util.xml import _parse, validate_xml


class xmlTest(unittest.TestCase):
    CORRELATE = xml

    def testValidateXml(self):
        self.assertTrue(validate_xml('<a><b/></a>'))
        self.assertRaises(etree.XMLSyntaxError, validate_xml, '<a>')
        self.assertFalse(validate_xml('<a>', silent=True))
        self.assertFalse(validate_xml('<a>\udcff</a>', silent=True))

    def testExternalEntitiesAreNotResolved(self):
        with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False) as fp:
            fp.write('XXE-MARKER')
        self.addCleanup(os.remove, fp.name)
        url = pathlib.Path(fp.name).as_uri()
        document = f'<!DOCTYPE r [<!ENTITY x SYSTEM "{url}">]><r>&x;</r>'
        for huge_tree in False, True:
            self.assertNotIn(b'XXE-MARKER', etree.tostring(_parse(document, huge_tree)))
