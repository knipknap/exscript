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
The main loop of the work queue, which starts the jobs.
"""

import logging
import threading
from collections.abc import Callable
from types import TracebackType
from typing import TYPE_CHECKING, Any

from ..util.event import Event
from .job import Job

if TYPE_CHECKING:
    from .job import Thread
    from .pipeline import Pipeline

_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())


class MainLoop(threading.Thread):
    """
    The thread that takes the jobs from the pipeline and starts them, and
    restarts each failed job until it has used up its attempts.

    job_init_event gets the Job before its first attempt. job_started_event,
    job_succeeded_event and job_aborted_event (after the last failed attempt)
    get the Thread of the attempt; job_error_event gets the Thread and the
    exception information. queue_empty_event gets no arguments.
    """

    def __init__(self, collection: 'Pipeline', job_cls: 'type[Thread]') -> None:
        """
        Constructor.

        :param collection: The pipeline of the jobs.
        :param job_cls: The class of the threads that run the jobs.
        """
        threading.Thread.__init__(self)
        self._logger = _logger
        self.job_init_event = Event()
        self.job_started_event = Event()
        self.job_error_event = Event()
        self.job_succeeded_event = Event()
        self.job_aborted_event = Event()
        self.queue_empty_event = Event()
        self.collection = collection
        self.job_cls = job_cls
        self.debug = 0
        self.daemon = True

    def _dbg(self, level: int, msg: str, exc_info: bool | BaseException | None = None) -> None:
        """
        Logs the given message if the debug level is at least the given level.
        """
        if level > self.debug:
            return
        self._logger.debug(msg, exc_info=exc_info)

    # Any: the data of the job, see job.Thread.__init__().
    def enqueue(
        self, function: 'Callable[[Thread], object]', name: str | None, times: int, data: Any
    ) -> str:
        """
        Appends a new job to the pipeline.

        :return: The id of the job.
        """
        job = Job(function, name, times, data)
        job.id = self.collection.append(job)
        return job.id

    # Any: the data of the job, see job.Thread.__init__().
    def enqueue_or_ignore(
        self, function: 'Callable[[Thread], object]', name: str | None, times: int, data: Any
    ) -> str | None:
        """
        Like enqueue(), but does nothing if a job with the given name is in
        the pipeline already.

        :return: The id of the new job, or None.
        """

        def conditional_append(queue: 'Pipeline') -> str | None:
            if queue.get_from_name(name) is not None:
                return None
            job = Job(function, name, times, data)
            job.id = queue.append(job, name)
            return job.id

        return self.collection.with_lock(conditional_append)

    # Any: the data of the job, see job.Thread.__init__().
    def priority_enqueue(
        self,
        function: 'Callable[[Thread], object]',
        name: str | None,
        force_start: bool,
        times: int,
        data: Any,
    ) -> str:
        """
        Adds a new job to the start of the pipeline.

        :param force_start: Whether to start the job even if the maximum
            number of jobs is in progress already.
        :return: The id of the job.
        """
        job = Job(function, name, times, data)
        job.id = self.collection.appendleft(job, name, force=force_start)
        return job.id

    # Any: the data of the job, see job.Thread.__init__().
    def priority_enqueue_or_raise(
        self,
        function: 'Callable[[Thread], object]',
        name: str | None,
        force_start: bool,
        times: int,
        data: Any,
    ) -> str | None:
        """
        Like enqueue_or_ignore(), but if a job with the given name is in the
        pipeline already, moves that job to the start of the pipeline, see
        Pipeline.prioritize().

        :param force_start: Whether to force the existing job.
        :return: The id of the new job, or None.
        """

        def conditional_append(queue: 'Pipeline') -> str | None:
            job = queue.get_from_name(name)
            if job is None:
                job = Job(function, name, times, data)
                job.id = queue.append(job, name)
                return job.id
            queue.prioritize(job, force=force_start)
            return None

        return self.collection.with_lock(conditional_append)

    def wait_for(self, job_id: str) -> None:
        """
        Waits until the job with the given id is removed from the pipeline.
        """
        self.collection.wait_for_id(job_id)

    def get_queue_length(self) -> int:
        """
        Returns the number of jobs in the pipeline, including those in
        progress.
        """
        return len(self.collection)

    def _on_job_completed(
        self,
        job: Job,
        exc_info: (
            tuple[type[BaseException] | None, BaseException | None, str | TracebackType | None]
            | None
        ),
    ) -> None:
        """
        Handles the end of an attempt of the given job, with the exception
        information of the attempt, or None. Emits the events, then restarts
        the job if it failed and has attempts left, else removes it from the
        pipeline. The watcher thread of the job calls this.
        """
        # This function is called in a sub-thread, so we need to be
        # careful that we are not in a lock while sending an event.
        self._dbg(4, 'Job "%s" called completed()' % job.name)

        try:
            # Notify listeners of the error
            # *before* removing the job from the queue.
            # This is because wait_until_done() depends on
            # get_queue_length() being 0, and we don't want a listener
            # to get a signal from a queue that already had
            # wait_until_done() completed.
            if exc_info:
                self._dbg(3, 'Error in job "%s"' % job.name)
                job.failures += 1
                self.job_error_event(job.child, exc_info)
                if job.failures >= job.times:
                    self._dbg(3, 'Job "%s" finally failed' % job.name)
                    self.job_aborted_event(job.child)
            else:
                self._dbg(3, 'Job "%s" succeeded.' % job.name)
                self.job_succeeded_event(job.child)

        finally:
            # Remove the watcher from the queue, and re-enque if needed.
            if exc_info and job.failures < job.times:
                self._dbg(3, 'Restarting job "%s"' % job.name)
                job.start(self.job_cls, self._on_job_completed, self.job_started_event)
            else:
                self.collection.task_done(job)

    def run(self) -> None:
        """
        Takes the jobs from the pipeline and starts them, until the pipeline
        is stopped.
        """
        while True:
            # Get the next job from the queue. This blocks until a task
            # is available or until self.collection.stop() is called.
            job = next(self.collection)
            if len(self.collection) <= 0:
                self.queue_empty_event()
            if job is None:
                break  # self.collection.stop() was called.

            self.job_init_event(job)
            job.start(self.job_cls, self._on_job_completed, self.job_started_event)
            self._dbg(3, 'Job "%s" started.' % job.name)
