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

class LoggerProxy(object):
    """
    An object that has a 1:1 relation to a logger object in another
    process.
    """
    def __init__(self, parent, logger, job):
        """
        Constructor.

        @type  parent: multiprocessing.Connection
        @param parent: A pipe to the associated queue.
        """
        self.parent    = parent
        self.logger_id = id(logger)
        self.job_id    = id(job)

    def log(self, string):
        self.parent.send(('log', (self.logger_id, self.job_id, string)))
