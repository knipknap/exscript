#
# Copyright (C) 2010-2017 Samuel Abels
# The MIT License (MIT)
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
The work queue, which runs functions in threads.
"""

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, cast

from ..util.event import Event
from .job import Thread
from .mainloop import MainLoop
from .pipeline import Pipeline

if TYPE_CHECKING:
    from .job import Job

_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())


def _check_mode(mode: str) -> None:
    """
    Raises an exception unless the given mode is 'threading': a ValueError
    for 'multiprocessing', else a TypeError.
    """
    if mode == 'multiprocessing':
        raise ValueError(
            "mode='multiprocessing' was removed in Exscript 3.0: jobs run in threads. "
            'For several CPU cores, run several processes yourself, or use the '
            'free-threaded build of Python.'
        )
    if mode != 'threading':
        raise TypeError('invalid "mode" argument: ' + repr(mode))


class WorkQueue:
    """
    This class implements the asynchronous workqueue and is the main API
    for using the workqueue module.
    """

    def __init__(
        self, collection: Pipeline | None = None, max_threads: int = 1, mode: str = 'threading'
    ) -> None:
        """
        Constructor.

        :param collection: The pipeline of the jobs. Defaults to a new
            Pipeline.
        :type  max_threads: int
        :param max_threads: The maximum number of concurrent threads.
        :type  mode: str
        :param mode: 'threading', the only mode; see _check_mode().
        """
        self._logger = _logger
        _check_mode(mode)
        self.job_cls = Thread
        if collection is None:
            self.collection = Pipeline(max_threads)
        else:
            self.collection = collection
            collection.set_max_working(max_threads)
        self.job_init_event = Event()
        self.job_started_event = Event()
        self.job_error_event = Event()
        self.job_succeeded_event = Event()
        self.job_aborted_event = Event()
        self.queue_empty_event = Event()
        self.debug = 0
        self.main_loop: MainLoop | None = None
        self._init()

    def _init(self) -> None:
        """
        Creates and starts a new main loop, and forwards its events to the
        events of the work queue.
        """
        self.main_loop = MainLoop(self.collection, self.job_cls)
        self.main_loop.debug = self.debug
        self.main_loop.job_init_event.listen(self.job_init_event)
        self.main_loop.job_started_event.listen(self.job_started_event)
        self.main_loop.job_error_event.listen(self.job_error_event)
        self.main_loop.job_succeeded_event.listen(self.job_succeeded_event)
        self.main_loop.job_aborted_event.listen(self.job_aborted_event)
        self.main_loop.queue_empty_event.listen(self.queue_empty_event)
        self.main_loop.start()

    # After this check, main_loop is not None; the methods that use it cast
    # it to MainLoop for the type checker.
    def _check_if_ready(self) -> None:
        """
        Raises an exception if the work queue has no main loop: after
        destroy(), or after shutdown() without restart.
        """
        if self.main_loop is None:
            raise Exception('main loop is already destroyed')

    def _dbg(self, level: int, msg: str, exc_info: bool | BaseException | None = None) -> None:
        """
        Logs the given message if the debug level is at least the given level.
        """
        if level > self.debug:
            return
        self._logger.debug(msg, exc_info=exc_info)

    def set_debug(self, level: int) -> None:
        """
        Set the debug level.

        :type  level: int
        :param level: The debug level.
        """
        self._check_if_ready()
        self.debug = level
        cast(MainLoop, self.main_loop).debug = level

    def get_max_threads(self) -> int:
        """
        Returns the maximum number of concurrent threads.

        :rtype:  int
        :return: The number of threads.
        """
        self._check_if_ready()
        return self.collection.get_max_working()

    def set_max_threads(self, max_threads: int) -> None:
        """
        Set the maximum number of concurrent threads.

        :type  max_threads: int
        :param max_threads: The number of threads.
        """
        if max_threads is None:
            raise TypeError('max_threads must not be None.')
        self._check_if_ready()
        self.collection.set_max_working(max_threads)

    # Any: the data of the job, see job.Thread.__init__().
    def enqueue(
        self,
        function: Callable[[Thread], object],
        name: str | None = None,
        times: int = 1,
        data: Any = None,
    ) -> str:
        """
        Appends a function to the queue for execution. The times argument
        specifies the number of attempts if the function raises an exception.
        If the name argument is None it defaults to whatever id(function)
        returns.

        :type  function: callable
        :param function: The function that is executed.
        :type  name: str
        :param name: Stored in Job.name.
        :type  times: int
        :param times: The maximum number of attempts.
        :type  data: object
        :param data: Optional data to store in Job.data.
        :rtype:  str
        :return: The id of the new job.
        """
        self._check_if_ready()
        return cast(MainLoop, self.main_loop).enqueue(function, name, times, data)

    # Any: the data of the job, see job.Thread.__init__().
    def enqueue_or_ignore(
        self,
        function: Callable[[Thread], object],
        name: str | None = None,
        times: int = 1,
        data: Any = None,
    ) -> str | None:
        """
        Like enqueue(), but does nothing if a function with the same name
        is already in the queue.
        Returns a job id if a new job was added, returns None otherwise.

        :type  function: callable
        :param function: The function that is executed.
        :type  name: str
        :param name: Stored in Job.name.
        :type  times: int
        :param times: The maximum number of attempts.
        :type  data: object
        :param data: Optional data to store in Job.data.
        :rtype:  str or None
        :return: The id of the new job.
        """
        self._check_if_ready()
        return cast(MainLoop, self.main_loop).enqueue_or_ignore(function, name, times, data)

    # Any: the data of the job, see job.Thread.__init__().
    def priority_enqueue(
        self,
        function: Callable[[Thread], object],
        name: str | None = None,
        force_start: bool = False,
        times: int = 1,
        data: Any = None,
    ) -> str:
        """
        Like :class:`enqueue()`, but adds the given function at the top of the
        queue.
        If force_start is True, the function is immediately started even when
        the maximum number of concurrent threads is already reached.

        :type  function: callable
        :param function: The function that is executed.
        :type  name: str
        :param name: Stored in Job.name.
        :type  force_start: bool
        :param force_start: Whether to start execution immediately.
        :type  times: int
        :param times: The maximum number of attempts.
        :type  data: object
        :param data: Optional data to store in Job.data.
        :rtype:  str
        :return: The id of the new job.
        """
        self._check_if_ready()
        return cast(MainLoop, self.main_loop).priority_enqueue(
            function, name, force_start, times, data
        )

    # Any: the data of the job, see job.Thread.__init__().
    def priority_enqueue_or_raise(
        self,
        function: Callable[[Thread], object],
        name: str | None = None,
        force_start: bool = False,
        times: int = 1,
        data: Any = None,
    ) -> str | None:
        """
        Like priority_enqueue(), but if a function with the same name is
        already in the queue, the existing function is moved to the top of
        the queue and the given function is ignored.
        Returns a job id if a new job was added, returns None otherwise.

        :type  function: callable
        :param function: The function that is executed.
        :type  name: str
        :param name: Stored in Job.name.
        :param force_start: Whether to start execution immediately.
        :type  times: int
        :param times: The maximum number of attempts.
        :type  data: object
        :param data: Optional data to store in Job.data.
        :rtype:  str or None
        :return: The id of the new job.
        """
        self._check_if_ready()
        return cast(MainLoop, self.main_loop).priority_enqueue_or_raise(
            function, name, force_start, times, data
        )

    def unpause(self) -> None:
        """
        Restart the execution of enqueued jobs after pausing them.
        This method is the opposite of pause().
        This method is asynchronous.
        """
        self.collection.unpause()

    def pause(self) -> None:
        """
        Stop the execution of enqueued jobs.
        Executing may later be resumed by calling unpause().
        This method is asynchronous.
        """
        self.collection.pause()

    def wait_for(self, job_id: str) -> None:
        """
        Waits until the job with the given id is completed.

        :type  job_id: str
        :param job_id: The id of the job.
        """
        self._check_if_ready()
        cast(MainLoop, self.main_loop).wait_for(job_id)

    def wait_until_done(self) -> None:
        """
        Waits until the queue is empty.
        """
        self.collection.wait_all()

    def shutdown(self, restart: bool = True) -> None:
        """
        Stop the execution of enqueued jobs, and wait for all running
        jobs to complete. This method is synchronous and returns as soon
        as all jobs are terminated (i.e. all threads are stopped).

        If restart is True, the workqueue is restarted, so you may fill it
        with new jobs; if it was paused, it stays paused.

        If restart is False, the WorkQueue can no longer be used after calling
        this method.

        :type  restart: bool
        :param restart: Whether to restart the queue after shutting down.
        """
        self._check_if_ready()
        self.collection.stop()
        self.collection.wait()
        cast(MainLoop, self.main_loop).join()
        self.main_loop = None
        self.collection.clear()
        if restart:
            self.collection.start()
            self._init()

    def destroy(self) -> None:
        """
        Like shutdown(), but does not restart the queue and does not
        wait for already started jobs to complete.
        """
        self._check_if_ready()
        self.collection.stop()
        cast(MainLoop, self.main_loop).join()
        self.main_loop = None
        self.collection.clear()

    def is_paused(self) -> bool:
        """
        Returns True if the queue is paused, shut down without restart or
        destroyed, False otherwise.

        :rtype:  bool
        :return: Whether enqueued jobs are currently not executed.
        """
        if self.main_loop is None:
            return True
        return self.collection.paused

    def get_running_jobs(self) -> 'list[Job]':
        """
        Returns a list of all jobs that are currently in progress.

        :rtype:  list[Job]
        :return: A list of running jobs.
        """
        return self.collection.get_working()

    def get_length(self) -> int:
        """
        Returns the number of currently non-completed jobs.

        :rtype:  int
        :return: The length of the queue.
        """
        return len(self.collection)
