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
from builtins import object
from Exscript.util.event import Event


class Task(object):

    """
    Represents a batch of running actions.
    """

    def __init__(self, workqueue):
        self.done_event = Event()
        self.workqueue = workqueue
        self.job_ids = set()
        self.completed = 0
        self.workqueue.job_succeeded_event.listen(self._on_job_done)
        self.workqueue.job_aborted_event.listen(self._on_job_done)

    def _on_job_done(self, job):
        if job.id not in self.job_ids:
            return
        self.completed += 1
        if self.is_completed():
            self.done_event()

    def is_completed(self):
        """
        Returns True if all actions in the task are completed, returns
        False otherwise.

        :rtype:  bool
        :return: Whether the task is completed.
        """
        return self.completed == len(self.job_ids)

    def wait(self):
        """
        Waits until all actions in the task have completed.
        Does not use any polling.
        """
        for theid in self.job_ids:
            self.workqueue.wait_for(theid)

    def add_job_id(self, theid):
        """
        Adds a job to the task.

        :type  theid: int
        :param theid: The id of the job.
        """
        self.job_ids.add(theid)
