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
Logging utilities.
"""
from Exscript.LoggerProxy import LoggerProxy

def logged(function, logger):
    """
    Wraps a function that has a connection passed such that everything that
    happens on the connection is logged using the given logger.

    @type  function: function
    @param function: The function that's ought to be wrapped.
    @type  logger: Logger
    @param logger: The logger that handles the logging.
    @rtype:  function
    @return: The wrapped function.
    """
    def decorated(job, conn, *args, **kwargs):
        proxy = LoggerProxy(job.data, logger, job)
        conn.data_received_event.listen(proxy.log)
        return function(job, conn, *args, **kwargs)
    return decorated
