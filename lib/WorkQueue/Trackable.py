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

class Slot(object):
    def __init__(self):
        self.subscribers = []

    def subscribe(self, func):
        self.subscribers.append(func)

    def emit(self, name, *args, **kwargs):
        for func in self.subscribers:
            func(name, *args, **kwargs)


class Trackable(object):
    def __init__(self):
        self.slots = {}

    def signal_connect(self, name, func):
        if not self.slots.has_key(name):
            self.slots[name] = Slot()
        self.slots[name].subscribe(func)

    def emit(self, name, *args, **kwargs):
        if not self.slots.has_key(name):
            return
        self.slots[name].emit(name, *args, **kwargs)
