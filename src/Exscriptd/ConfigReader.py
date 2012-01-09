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
import inspect
import shutil
from lxml           import etree
from Exscriptd.util import resolve_variables

class ConfigReader(object):
    def __init__(self, filename, resolve_variables = True, parent = None):
        clsfile        = inspect.getfile(self.__class__)
        self.resolve   = resolve_variables
        self.cfgtree   = etree.parse(filename)
        self.filename  = filename
        self.parent    = parent
        self.variables = os.environ.copy()
        self.variables['INSTALL_DIR'] = os.path.dirname(clsfile)
        self._clean_tree()

    def _resolve(self, text):
        if not self.resolve:
            return text
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
            if element.tag is etree.Comment:
                continue
            element.text = self._resolve(element.text)
            for attr in element.attrib:
                value                = element.attrib[attr]
                element.attrib[attr] = self._resolve(value)

    def _add_or_update_elem(self, parent, name, text):
        child_elem = parent.find(name)
        changed    = False
        if child_elem is None:
            changed    = True
            child_elem = etree.SubElement(parent, name)
        if str(child_elem.text) != str(text):
            changed         = True
            child_elem.text = str(text)
        return changed

    def _write_xml(self, tree, filename):
        if os.path.isfile(filename):
            shutil.move(filename, filename + '.old')
        with open(filename, 'w') as fp:
            fp.write(etree.tostring(tree, pretty_print = True))

    def _findelem(self, selector):
        elem = self.cfgtree.find(selector)
        if elem is not None:
            return elem
        if self.parent is None:
            return None
        return self.parent._findelem(selector)

    def save(self):
        self._write_xml(self.cfgtree, self.filename)
