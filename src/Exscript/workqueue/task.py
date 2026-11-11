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
Represents a batch of enqueued actions.
"""

import threading
from typing import TYPE_CHECKING

from Exscript.util.event import Event

if TYPE_CHECKING:
    from .job import Thread
    from .workqueue import WorkQueue


class Task:
    """
    Represents a batch of running actions.
    """

    def __init__(self, workqueue: 'WorkQueue') -> None:
        """
        Constructor. The task listens to the events of the given work queue
        to count its completed jobs; its done_event is emitted when all are
        completed.

        :param workqueue: The work queue that runs the jobs of the task.
        """
        self.done_event = Event()
        self.workqueue = workqueue
        self.job_ids: set[str] = set()
        self.completed = 0
        self.lock = threading.Lock()  # for completed; jobs end in several threads
        self.workqueue.job_succeeded_event.listen(self._on_job_done)
        self.workqueue.job_aborted_event.listen(self._on_job_done)

    def _on_job_done(self, job: 'Thread') -> None:
        """
        Counts the given job as completed if it belongs to the task, and
        emits done_event when all jobs of the task are completed. Counts and
        checks under the lock, so that jobs that end at the same time are
        all counted, and only the last one emits done_event.
        """
        if job.id not in self.job_ids:
            return
        with self.lock:
            self.completed += 1
            done = self.is_completed()
        if done:
            self.done_event()

    def is_completed(self) -> bool:
        """
        Returns True if all actions in the task are completed, returns
        False otherwise.

        :rtype:  bool
        :return: Whether the task is completed.
        """
        return self.completed == len(self.job_ids)

    def wait(self) -> None:
        """
        Waits until all actions in the task have completed.
        Does not use any polling.
        """
        for theid in self.job_ids:
            self.workqueue.wait_for(theid)

    def add_job_id(self, theid: str) -> None:
        """
        Adds a job to the task.

        :type  theid: str
        :param theid: The id of the job.
        """
        self.job_ids.add(theid)
