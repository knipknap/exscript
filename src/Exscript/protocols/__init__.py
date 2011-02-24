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
from Exscript                    import Account
from Exscript.util.url           import Url
from Exscript.protocols.Protocol import Protocol
from Exscript.protocols.Telnet   import Telnet
from Exscript.protocols.SSH2     import SSH2
from Exscript.protocols.Dummy    import Dummy

protocol_map = {'dummy':  Dummy,
                'pseudo': Dummy,
                'telnet': Telnet,
                'ssh':    SSH2,
                'ssh2':   SSH2}

def get_protocol_from_name(name):
    """
    Returns the protocol class for the protocol with the given name.
    """
    cls = protocol_map.get(name)
    if not cls:
        raise ValueError('Unsupported protocol "%s".' % name)
    return cls

def create_protocol(name, **kwargs):
    """
    Returns an instance of the protocol with the given name.
    """
    cls = protocol_map.get(name)
    if not cls:
        raise ValueError('Unsupported protocol "%s".' % name)
    return cls(**kwargs)

def connect(uri, default_protocol = 'telnet', **kwargs):
    """
    Parses the given URL-formatted hostname using L{Exscript.util.url},
    creates an instance of the protocol, and calls L{Protocol.connect()}
    on it. If the URL contains a username, L{Protocol.login()} is also
    called.

    @type  uri: str
    @param uri: The URL-formatted hostname.
    @type  default_protocol: str
    @param default_protocol: Protocol that is used if the URL specifies none.
    @type  kwargs: dict
    @param kwargs: Passed to the protocol constructor.
    """
    url  = Url.from_string(uri, default_protocol)
    conn = create_protocol(url.protocol, **kwargs)
    conn.connect(url.hostname)

    if url.username is not None \
       or url.password1 is not None \
       or url.password2:
        account = Account(url.username, url.password1, url.password2)
        conn.login(account)

    return conn

import inspect 
__all__ = [name for name, obj in locals().items()
           if not (name.startswith('_') or inspect.ismodule(obj))]
