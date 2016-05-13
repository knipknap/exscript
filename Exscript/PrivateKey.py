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
Represents a private key.
"""
from builtins import object
from paramiko import RSAKey, DSSKey
from paramiko.ssh_exception import SSHException


class PrivateKey(object):

    """
    Represents a cryptographic key, and may be used to authenticate
    useing :class:`Exscript.protocols`.
    """
    keytypes = set()

    def __init__(self, keytype='rsa'):
        """
        Constructor. Supported key types are provided by their respective
        protocol adapters and can be retrieved from the PrivateKey.keytypes
        class attribute.

        :type  keytype: string
        :param keytype: The key type.
        """
        if keytype not in self.keytypes:
            raise TypeError('unsupported key type: ' + repr(keytype))
        self.keytype = keytype
        self.filename = None
        self.password = None

    @staticmethod
    def from_file(filename, password='', keytype=None):
        """
        Returns a new PrivateKey instance with the given attributes.
        If keytype is None, we attempt to automatically detect the type.

        :type  filename: string
        :param filename: The key file name.
        :type  password: string
        :param password: The key password.
        :type  keytype: string
        :param keytype: The key type.
        :rtype:  PrivateKey
        :return: The new key.
        """
        if keytype is None:
            try:
                key = RSAKey.from_private_key_file(filename)
                keytype = 'rsa'
            except SSHException as e:
                try:
                    key = DSSKey.from_private_key_file(filename)
                    keytype = 'dss'
                except SSHException as e:
                    msg = 'not a recognized private key: ' + repr(filename)
                    raise ValueError(msg)
        key = PrivateKey(keytype)
        key.filename = filename
        key.password = password
        return key

    def get_type(self):
        """
        Returns the type of the key, e.g. RSA or DSA.

        :rtype:  string
        :return: The key type
        """
        return self.keytype

    def set_filename(self, filename):
        """
        Sets the name of the key file to use.

        :type  filename: string
        :param filename: The key filename.
        """
        self.filename = filename

    def get_filename(self):
        """
        Returns the name of the key file.

        :rtype:  string
        :return: The key password.
        """
        return self.filename

    def set_password(self, password):
        """
        Defines the password used for decrypting the key.

        :type  password: string
        :param password: The key password.
        """
        self.password = password

    def get_password(self):
        """
        Returns the password for the key.

        :rtype:  string
        :return: The key password.
        """
        return self.password
