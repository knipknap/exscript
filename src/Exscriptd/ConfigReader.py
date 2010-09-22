# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import os
from lxml import etree
from util import resolve_variables

class ConfigReader(object):
    def __init__(self, filename):
        self.cfgtree   = etree.parse(filename)
        self.variables = os.environ.copy()
        self._clean_tree()

    def _resolve(self, text):
        if text is None:
            return None
        return resolve_variables(self.variables, text.strip())

    def _clean_tree(self):
        # Read all variables.
        variables = self.cfgtree.find('variables')
        if variables is not None:
            for element in variables:
                varname = element.tag.strip()
                value   = resolve_variables(self.variables, element.text)
                self.variables[varname] = value

        # Resolve variables everywhere.
        for element in self.cfgtree.iter():
            element.text = self._resolve(element.text)
            for attr in element.attrib:
                value                = element.attrib[attr]
                element.attrib[attr] = self._resolve(value)
