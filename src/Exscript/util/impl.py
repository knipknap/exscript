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
"""
Development tools.
"""
import warnings

def deprecation(msg):
    """
    Prints a deprecation warning.
    """
    warnings.warn('deprecated',
                  category   = DeprecationWarning,
                  stacklevel = 2)

def deprecated(func):
    """
    A decorator for marking functions as deprecated. Results in
    a printed warning message when the function is used.
    """
    def decorated(*args, **kwargs):
        warnings.warn('Call to deprecated function %s.' % func.__name__,
                      category   = DeprecationWarning,
                      stacklevel = 2)
        return func(*args, **kwargs)
    decorated.__name__ = func.__name__
    decorated.__doc__  = func.__doc__
    decorated.__dict__.update(func.__dict__)
    return decorated
