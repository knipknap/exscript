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
from functools import partial
from Exscript.Logger import get_manager
from Exscript.util.impl import serializeable_sys_exc_info

def log_to(logger):
    """
    Wraps a function that has a connection passed such that everything that
    happens on the connection is logged using the given logger.

    @type  logger: Logger
    @param logger: The logger that handles the logging.
    """
    def decorator(function):
        def decorated(job, conn, *args, **kwargs):
            logger.add_log(id(job), job.name, job.failures + 1)
            log_cb = partial(logger.log, id(job))
            conn.data_received_event.listen(log_cb)
            try:
                result = function(job, conn, *args, **kwargs)
            except:
                logger.log_aborted(id(job), serializeable_sys_exc_info())
                raise
            else:
                logger.log_succeeded(id(job))
            finally:
                conn.data_received_event.disconnect(log_cb)
            return result
        return decorated
    return decorator

def log_to_file(logdir, mode = 'a', delete = False, clearmem = True):
    """
    Like L{log_to()}, but automatically creates a new FileLogger
    instead of having one passed.
    """
    manager = get_manager()
    logger  = manager.FileLogger(logdir, mode, delete, clearmem)
    return log_to(logger)
