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
import os

def chmod(scope, filenames, mode):
    for filename in filenames:
        os.chmod(filename, mode[0])
    return True

def clear(scope, filename):
    file = open(filename[0], 'w')
    file.close()
    return True

def exists(scope, filename):
    return [os.path.exists(f) for f in filename]

def mkdir(scope, dirnames, mode = None):
    for dirname in dirnames:
        if mode is None:
            os.makedirs(dirname)
        else:
            os.makedirs(dirname, mode[0])
    return True

def read(scope, filename):
    file  = open(filename[0], 'r')
    lines = file.readlines()
    file.close()
    scope.define(_buffer = lines)
    return lines

def rm(scope, filenames):
    for filename in filenames:
        os.remove(filename)
    return True

def write(scope, filename, lines, mode = ['a']):
    file = open(filename[0], mode[0])
    file.writelines(['%s\n' % line.rstrip() for line in lines])
    file.close()
    return True
