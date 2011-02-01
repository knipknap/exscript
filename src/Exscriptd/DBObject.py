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

class DBObject(object):
    def __init__(self, obj = None):
        # Since we override setattr below, we can't access our properties
        # directly.
        self.__dict__['__object__']  = obj
        self.__dict__['__changed__'] = True

    def __setattr__(self, name, value):
        """
        Overwritten to proxy any calls to the associated object
        (decorator pattern).

        @type  name: string
        @param name: The attribute name.
        @type  value: string
        @param value: The attribute value.
        """
        if self.__dict__.get('__object__') is None:
            self.__dict__[name] = value
        if name in self.__dict__.keys():
            self.__dict__[name] = value
        else:
            setattr(self.__object__, name, value)

    def __getattr__(self, name):
        """
        Overwritten to proxy any calls to the associated object
        (decorator pattern).

        @type  name: string
        @param name: The attribute name.
        @rtype:  object
        @return: Whatever the protocol adapter returns.
        """
        if self.__dict__.get('__object__') is None:
            return self.__dict__[name]
        if name in self.__dict__.keys():
            return self.__dict__[name]
        return getattr(self.__object__, name)

    def touch(self):
        self.__dict__['__changed__'] = True

    def untouch(self):
        self.__dict__['__changed__'] = False

    def is_dirty(self):
        return self.__dict__['__changed__']
