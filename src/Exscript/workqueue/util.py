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
Useful utilities and decorators.
"""
from functools import wraps

def takes_job(function):
    """
    Any function that is marked with this decorator and placed in the
    L{Exscript.workqueue.WorkQueue} (using
    L{Exscript.workqueue.WorkQueue.enqueue()} or similar) will have the
    L{Exscript.workqueue.Job} object passed as an additional argument.
    This allows for better control over the threading behavior, and
    for accessing the associated data.

    @type  function: function
    @param function: The function that is wrapped.
    @rtype:  function
    @return: The wrapped function.
    """
    @wraps(function)
    def wrapper(*args, **kwargs):
        return function(*args, **kwargs)
    wrapper._takes_job = True
    return wrapper

def test_takes_job(function):
    """
    Returns True if the given function has the L{takes_job()} decorator,
    returns False otherwise.

    @type  function: function
    @param function: The function to test.
    @rtype:  bool
    @return: Whether the function has the decorator.
    """
    return hasattr(function, '_takes_job')
