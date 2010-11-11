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
from Exscript.external.SpiffSignal import Trackable
from MainLoop                      import MainLoop

class WorkQueue(Trackable):
    """
    This class implements the asynchronous workqueue and is the main API
    for using the workqueue module.
    """
    def __init__(self, **kwargs):
        """
        Constructor.

        @type  kwargs: dict
        @param kwargs: The following keyword arguments are supported:
                 debug: The debug level (default is 0)
                 max_threads: Number of concurrent connections (default is 1).
        """
        Trackable.__init__(self)
        self.debug       = kwargs.get('debug',       0)
        self.max_threads = kwargs.get('max_threads', 1)
        self._init()

    def _init(self):
        self.main_loop       = MainLoop()
        self.main_loop.debug = self.debug
        self.main_loop.set_max_threads(self.max_threads)
        self.main_loop.signal_connect('job-started',   self._on_job_started)
        self.main_loop.signal_connect('job-succeeded', self._on_job_succeeded)
        self.main_loop.signal_connect('job-aborted',   self._on_job_aborted)
        self.main_loop.signal_connect('job-completed', self._on_job_completed)
        self.main_loop.signal_connect('queue-empty',   self._on_queue_empty)
        self.main_loop.start()

    def _check_if_ready(self):
        if self.main_loop is None:
            raise Exception('main loop is already destroyed')

    def _on_job_started(self, job):
        """
        Called whenever a new thread was started.

        @type  job: Job
        @param job: The job that was started.
        """
        self.signal_emit('job-started', job)

    def _on_job_succeeded(self, job):
        """
        Called whenever a thread was succeeded.

        @type  job: Job
        @param job: The job that was succeeded.
        """
        self.signal_emit('job-succeeded', job)

    def _on_job_aborted(self, job, exception):
        """
        Called whenever a thread was aborted.

        @type  job: Job
        @param job: The job that was aborted.
        @type  exception: object
        @param exception: The exception that was thrown.
        """
        self.signal_emit('job-aborted', job, exception)

    def _on_job_completed(self, job):
        """
        Called whenever a thread was completed.

        @type  job: Job
        @param job: The job that was completed.
        """
        self.signal_emit('job-completed', job)

    def _on_queue_empty(self):
        """
        Called as soon as the queue is empty.

        @type  job: Job
        @param job: The job that was completed.
        """
        self.signal_emit('queue-empty')

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

    def shutdown(self):
        """
        Stop the execution of enqueued actions, and terminate any running
        actions. This method is synchronous and returns as soon as all actions
        are terminated (i.e. all threads are stopped).

        Once all actions are terminated, the queue is emptied and paused,
        so you may fill it with new actions.
        """
        self._check_if_ready()
        self.main_loop.shutdown()
        self.main_loop.join()
        self.main_loop = None
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
