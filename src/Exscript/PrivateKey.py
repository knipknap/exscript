# Copyright (C) 2007-2011 Samuel Abels.
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
"""
Represents a private key.
"""

class PrivateKey(object):
    keytypes = set()

    def __init__(self, keytype = 'rsa'):
        """
        Constructor. Supported key types are provided by their respective
        protocol adapters and can be retrieved from the PrivateKey.keytypes
        class attribute.

        @type  keytype: string
        @param keytype: The key type.
        """
        if keytype not in self.keytypes:
            raise TypeError('unsupported key type: ' + repr(keytype))
        self.keytype  = keytype
        self.filename = None
        self.password = None

    @staticmethod
    def from_file(filename, password = '', keytype = 'rsa'):
        """
        Returns a new PrivateKey instance with the given attributes.

        @type  filename: string
        @param filename: The key file name.
        @type  password: string
        @param password: The key password.
        @type  keytype: string
        @param keytype: The key type.
        @rtype:  PrivateKey
        @return: The new key.
        """
        key          = PrivateKey(keytype)
        key.filename = filename
        key.password = password
        return key

    def get_type(self):
        """
        Returns the type of the key, e.g. RSA or DSA.

        @rtype:  string
        @return: The key type
        """
        return self.keytype

    def set_filename(self, filename):
        """
        Sets the name of the key file to use.

        @type  filename: string
        @param filename: The key filename.
        """
        self.filename = filename

    def get_filename(self):
        """
        Returns the name of the key file.

        @rtype:  string
        @return: The key password.
        """
        return self.filename

    def set_password(self, password):
        """
        Defines the password used for decrypting the key.

        @type  password: string
        @param password: The key password.
        """
        self.password = password

    def get_password(self):
        """
        Returns the password for the key.

        @rtype:  string
        @return: The key password.
        """
        return self.password
