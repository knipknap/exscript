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
import sys
import Crypto
from Exscript.workqueue import Action
from Exscript.workqueue.util import test_takes_job
from Exscript.util.event import Event

class CustomAction(Action):
    """
    An action that calls the associated function and implements retry and
    logging.
    """
    def __init__(self, name, logname = None):
        """
        Constructor.

        @type  function: function
        @param function: Called when the action is executed.
        @type  name: str
        @param name: A name for the action.
        """
        Action.__init__(self)
        self.name      = name
        self.logname   = logname is not None and logname or name
        self.log_event = Event()
        self.attempt   = 1
        self.function  = None

        # Since each action is created in it's own thread, we must
        # re-initialize the random number generator to make sure that
        # child threads have no way of guessing the numbers of the parent.
        # If we don't, PyCrypto generates an error message for security
        # reasons.
        try:
            Crypto.Random.atfork()
        except AttributeError:
            # pycrypto versions that have no "Random" module also do not
            # detect the missing atfork() call, so they do not raise.
            pass

    def get_name(self):
        return self.name

    def get_logname(self):
        logname = self.logname
        if self.attempt > 1:
            logname += '_retry%d' % (self.attempt - 1)
        return logname + '.log'

    def execute(self, job):
        if self.function is not None:
            if test_takes_job(self.function):
                return self.function(job)
            else:
                return self.function()
