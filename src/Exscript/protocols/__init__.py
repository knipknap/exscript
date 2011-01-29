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
from Transport import Transport
from Telnet    import Telnet
from SSH2      import SSH2
from Dummy     import Dummy

protocol_map = {'dummy':  Dummy,
                'pseudo': Dummy,
                'telnet': Telnet,
                'ssh':    SSH2,
                'ssh2':   SSH2}

def get_protocol_from_name(name):
    """
    Returns the transport class for the protocol with the given name.
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

import inspect 
__all__ = [name for name, obj in locals().items()
           if not (name.startswith('_') or inspect.ismodule(obj))]
