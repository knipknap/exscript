#
# Copyright (C) 2010-2017 Samuel Abels
# The MIT License (MIT)
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Working with XML.
"""

from lxml import etree


class XMLValidationError(Exception):
    """
    Raised when XML validation fails.

    Provides the XML string that failed in its `xmlstring` attribute.
    """
    def __init__(self, *args: object, xmlstring=None) -> None:
        super().__init__(*args)
        self.xmlstring = xmlstring


def validate_xml(string, *, silent=False):
    """
    Try to parse the given string as XML to verify its syntax.

    Raises UnicodeEncodeError when the string cannot be encoded to UTF-8.
    Raises lxml.etree.XMLSyntaxError when the string is not valid XML.

    :param string: The string to validate.
    :param silent: Whether to suppress the exceptions and just return a boolean.
    :rtype: bool
    :return: Whether the string is valid XML in UTF-8.
    """
    try:
        etree.fromstring(string.encode("utf-8"))
    except UnicodeEncodeError:
        if not silent:
            raise
        return False
    except etree.XMLSyntaxError:
        if not silent:
            raise
        return False
    return True
