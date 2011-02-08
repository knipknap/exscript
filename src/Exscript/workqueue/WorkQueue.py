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
from Exscript.util.event         import Event
from Exscript.workqueue.MainLoop import MainLoop

class WorkQueue(object):
    """
    This class implements the asynchronous workqueue and is the main API
    for using the workqueue module.
    """
    def __init__(self, **kwargs):
        """
        Constructor.

        @keyword debug: The debug level (default is 0)
        @keyword max_threads: Number of concurrent connections (default is 1).
        """
        self.job_started_event   = Event()
        self.job_succeeded_event = Event()
        self.job_aborted_event   = Event()
        self.job_completed_event = Event()
        self.queue_empty_event   = Event()
        self.debug               = kwargs.get('debug',       0)
        self.max_threads         = kwargs.get('max_threads', 1)
        self.main_loop           = None
        self._init()

    def _init(self):
        self.main_loop       = MainLoop()
        self.main_loop.debug = self.debug
        self.main_loop.set_max_threads(self.max_threads)
        self.main_loop.job_started_event.listen(self.job_started_event)
        self.main_loop.job_succeeded_event.listen(self.job_succeeded_event)
        self.main_loop.job_aborted_event.listen(self.job_aborted_event)
        self.main_loop.job_completed_event.listen(self.job_completed_event)
        self.main_loop.queue_empty_event.listen(self.queue_empty_event)
        self.main_loop.start()

    def _check_if_ready(self):
        if self.main_loop is None:
            raise Exception('main loop is already destroyed')

    def set_debug(self, debug = 1):
        """
        Set the debug level.

        @type  debug: int
        @param debug: The debug level.
        """
        self._check_if_ready()
        self.debug           = debug
        self.main_loop.debug = debug

    def get_max_threads(self):
        """
        Returns the maximum number of concurrent threads.

        @rtype:  int
        @return: The number of threads.
        """
        self._check_if_ready()
        return self.main_loop.get_max_threads()

    def set_max_threads(self, max_threads):
        """
        Set the maximum number of concurrent threads.

        @type  max_threads: int
        @param max_threads: The number of threads.
        """
        if max_threads is None:
            raise TypeError('max_threads must not be None.')
        self._check_if_ready()
        self.max_threads = max_threads
        self.main_loop.set_max_threads(max_threads)

    def enqueue(self, action):
        """
        Appends an action to the queue for execution.

        @type  action: Action
        @param action: The action that is executed.
        """
        self._check_if_ready()
        self.main_loop.enqueue(action)

    def enqueue_or_ignore(self, action):
        """
        Like enqueue(), but does nothing if an action with the same name
        is already in the queue.

        @type  action: Action
        @param action: The action that is executed.
        @rtype:  bool
        @return: True if the action was enqueued, False otherwise.
        """
        self._check_if_ready()
        return self.main_loop.enqueue_or_ignore(action)

    def priority_enqueue(self, action, force_start = False):
        """
        Add the given action at the top of the queue.
        If force_start is True, the action is immediately started even when 
        the maximum number of concurrent threads is already reached.

        @type  action: Action
        @param action: The action that is executed.
        @type  force_start: bool
        @param force_start: Whether to start execution immediately.
        """
        self._check_if_ready()
        self.main_loop.priority_enqueue(action, force_start)

    def priority_enqueue_or_raise(self, action, force_start = False):
        """
        Like priority_enqueue(), but if an action with the same name is
        already in the queue, the existing action is moved to the top of
        the queue and the given action is ignored.

        @type  action: Action
        @param action: The action that is executed.
        @rtype:  bool
        @return: True if the action was enqueued, False otherwise.
        """
        self._check_if_ready()
        return self.main_loop.priority_enqueue_or_raise(action, force_start)

    def unpause(self):
        """
        Restart the execution of enqueued actions after pausing them.
        This method is the opposite of pause().
        This method is asynchronous.
        """
        self._check_if_ready()
        self.main_loop.resume()

    def pause(self):
        """
        Stop the execution of enqueued actions.
        Executing may later be resumed by calling unpause().
        This method is asynchronous.
        """
        self._check_if_ready()
        self.main_loop.pause()

    def wait_for(self, action):
        """
        Waits until the given action is completed.

        @type  action: Action
        @param action: The action that is executed.
        """
        self._check_if_ready()
        self.main_loop.wait_for(action)

    def wait_for_activity(self):
        """
        Waits until any change has happened, such as a job as completed
        or a new job was enqueued. This method can be useful for avoiding
        polling.
        """
        self._check_if_ready()
        self.main_loop.wait_for_activity()

    def wait_until_done(self):
        """
        Waits until the queue is empty.
        """
        if self.main_loop is None:
            return
        self.main_loop.wait_until_done()

    def shutdown(self, restart = True):
        """
        Stop the execution of enqueued actions, and terminate any running
        actions. This method is synchronous and returns as soon as all actions
        are terminated (i.e. all threads are stopped).

        If restart is True, the workqueue is restarted and paused,
        so you may fill it with new actions.

        If restart is False, the WorkQueue can no longer be used after calling
        this method.

        @type  restart: bool
        @param restart: Whether to restart the queue after shutting down.
        """
        self._check_if_ready()
        self.main_loop.shutdown()
        self.main_loop.join()
        self.main_loop = None
        if restart:
            self._init()

    def is_paused(self):
        """
        Returns True if the queue is currently being worked (i.e. not stopped 
        and not shut down), False otherwise.

        @rtype:  bool
        @return: Whether enqueued actions are executed.
        """
        if self.main_loop is None:
            return True
        return self.main_loop.is_paused()

    def in_queue(self, action):
        """
        Returns True if the given action is currently in the queue or in 
        progress. Returns False otherwise.

        @type  action: Action
        @param action: The action that is executed.
        @rtype:  bool
        @return: Whether the action is currently in the queue.
        """
        if self.main_loop is None:
            return False
        return self.main_loop.in_queue(action)

    def in_progress(self, action):
        """
        Returns True if the given action is currently in progress.
        Returns False otherwise.

        @type  action: Action
        @param action: The action that is executed.
        @rtype:  bool
        @return: Whether the action is currently in progress.
        """
        if self.main_loop is None:
            return False
        return self.main_loop.in_progress(action)

    def get_running_actions(self):
        """
        Returns a list of all actions that are currently in progress.

        @rtype:  list[Action]
        @return: A list of running actions.
        """
        if self.main_loop is None:
            return []
        return self.main_loop.get_running_actions()

    def get_length(self):
        """
        Returns the number of currently non-completed actions.

        @rtype:  int
        @return: The length of the queue.
        """
        if self.main_loop is None:
            return 0
        return self.main_loop.get_queue_length()
