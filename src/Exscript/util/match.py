# Copyright (C) 2007 Samuel Abels, http://debain.org
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
import re
from Exscript import Connection

def _first_match(string, compiled):
    match = compiled.search(string)
    if match is None and compiled.groups <= 1:
        return None
    elif match is None:
        return [None for i in range(0, compiled.groups)]
    elif compiled.groups == 0:
        return string
    elif compiled.groups == 1:
        return match.groups(1)[0]
    else:
        return [match.groups(i)[0] for i in range(1, compiled.groups + 1)]


def first_match(string, regex, flags = re.M):
    if isinstance(string, Connection):
        string = string.response
    return _first_match(string, re.compile(regex, flags))


def any_match(string, regex):
    if isinstance(string, Connection):
        string = string.response
    compiled = re.compile(regex)
    results  = []
    if compiled.groups <= 1:
        for line in string.split('\n'):
            match = _first_match(line, compiled)
            if match is None:
                continue
            results.append(match)
    else:
        for line in string.split('\n'):
            match = _first_match(line, compiled)
            if match[0] is None:
                continue
            results.append(match)
    return results
