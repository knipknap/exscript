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
import Crypto
from Exscript.workqueue             import Action
from Exscript.util.event            import Event
from Exscript.protocols.Exception   import LoginFailure
from Exscript.interpreter.Exception import FailException
from Exscript.parselib.Exception    import CompileError
from Exscript.AccountProxy          import AccountProxy

class CustomAction(Action):
    """
    An action that calls the associated function and implements retry and
    logging.
    """
    def __init__(self, accm, function, name):
        """
        Constructor.

        @type  accm: multiprocessing.Connection
        @param accm: A pipe to the associated account manager.
        @type  function: function
        @param function: Called when the action is executed.
        @type  name: str
        @param name: A name for the action.
        """
        Action.__init__(self)
        self.started_event   = Event()
        self.error_event     = Event()
        self.aborted_event   = Event()
        self.succeeded_event = Event()
        self.accm            = accm
        self.function        = function
        self.times           = 1
        self.login_times     = 1
        self.failures        = 0
        self.login_failures  = 0
        self.aborted         = False
        self.name            = name

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

    def acquire_account(self, account_hash):
        # Specific account requested?
        if account:
            return AccountProxy.for_account(self.accm, account)
        else:
            return AccountProxy.for_random_account(self.accm)

        # Is a default account defined for this connection?
        account = self.get_host().get_account()
        if account:
            return AccountProxy.for_account(self.accm, account)

        # Else, let the account manager assign an account.
        return AccountProxy.for_host(self.accm, self.get_host())

    def release_account(self, account):
        account.release()

    def get_logname(self):
        logname = self.get_name()
        retries = self.n_failures()
        if retries > 0:
            logname += '_retry%d' % retries
        return logname + '.log'

    def set_times(self, times):
        self.times = int(times)

    def set_login_times(self, times):
        """
        The number of login attempts.
        """
        self.login_times = int(times)

    def n_failures(self):
        return self.failures + self.login_failures

    def has_aborted(self):
        return self.aborted

    def _is_recoverable_error(self, exc):
        for cls in (CompileError, FailException):
            if isinstance(exc, cls):
                return False
        return True

    def _create_connection(self):
        return None

    def _call_function(self, conn):
        return self.function()

    def execute(self):
        try:
            while self.failures < self.times \
              and self.login_failures < self.login_times:
                conn = self._create_connection()
                self.started_event(self, conn)

                # Execute the user-provided function.
                try:
                    self._call_function(conn)
                except LoginFailure, e:
                    self.error_event(self, e)
                    self.login_failures += 1
                    continue
                except Exception, e:
                    self.error_event(self, e)
                    self.failures += 1
                    if not self._is_recoverable_error(e):
                        break
                    continue

                self.succeeded_event(self)
                return

            # Ending up here the function finally failed.
            self.aborted = True
            self.aborted_event(self)
        finally:
            self.accm.close()
