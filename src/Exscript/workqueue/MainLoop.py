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
import threading
import multiprocessing
from copy import copy
from multiprocessing import Pipe
from Exscript.util.event import Event
from Exscript.workqueue.Pipeline import Pipeline

# See http://bugs.python.org/issue1731717
multiprocessing.process._cleanup = lambda: None

class _ChildWatcher(threading.Thread):
    def __init__(self, child, callback):
        threading.Thread.__init__(self, name = child.name)
        self.child = child
        self.cb    = callback

    def __copy__(self):
        watcher = _ChildWatcher(copy(self.child), self.cb)
        return watcher

    def run(self):
        to_child, to_self = Pipe()
        try:
            self.child.start(to_self)
            result = to_child.recv()
            self.child.join()
        except:
            result = sys.exc_info()
        finally:
            to_child.close()
            to_self.close()
        if result == '':
            self.cb(self, None)
        else:
            self.cb(self, result)

class MainLoop(threading.Thread):
    def __init__(self, job_cls):
        threading.Thread.__init__(self)
        self.job_init_event      = Event()
        self.job_started_event   = Event()
        self.job_error_event     = Event()
        self.job_succeeded_event = Event()
        self.job_aborted_event   = Event()
        self.queue_empty_event   = Event()
        self.collection          = Pipeline()
        self.job_cls             = job_cls
        self.debug               = 5
        self.daemon              = True

    def _dbg(self, level, msg):
        if self.debug >= level:
            print msg

    def get_max_threads(self):
        return self.queue.max_working

    def set_max_threads(self, max_threads):
        self.queue.set_max_working(max_threads)

    def _create_job(self, function, name, times, data):
        if name is None:
            name = str(id(function))
        job     = self.job_cls(function, name, times, data)
        watcher = _ChildWatcher(job, self._on_job_completed)
        return watcher

    def enqueue(self, function, name, times, data):
        job = self._create_job(function, name, times, data)
        self.collection.append(job)
        return job.child.id

    def enqueue_or_ignore(self, function, name, times, data):
        def conditional_append(queue):
            if queue.find(lambda x: x.name == name) is not None:
                return None
            job = self._create_job(function, name, times, data)
            queue.append(job)
            return job.child.id
        return self.collection.with_lock(conditional_append)

    def priority_enqueue(self, function, name, force_start, times, data):
        job = self._create_job(function, name, times, data)
        self.collection.appendleft(job, force_start)
        return job.child.id

    def priority_enqueue_or_raise(self,
                                  function,
                                  name,
                                  force_start,
                                  times,
                                  data):
        def conditional_append(queue):
            job = queue.find(lambda x: x.name == name)
            if job is None:
                job = self._create_job(function, name, times, data)
                queue.append(job)
                return job.child.id
            queue.prioritize(job)
            return None
        return self.collection.with_lock(conditional_append)

    def pause(self):
        self.collection.pause()

    def resume(self):
        self.collection.unpause()

    def is_paused(self):
        return self.collection.paused

    def wait_for(self, job_id):
        job = self.collection.find(lambda x: x.child.id == job_id)
        if job:
            self.collection.wait_for_id(id(job))

    def wait_until_done(self):
        self.collection.wait_all()

    def shutdown(self, force = False):
        self.collection.stop()
        if not force:
            self.collection.wait()

    def _start_job(self, job, notify = True):
        if notify:
            self.job_init_event(job.child)

        job.start()

        if notify:
            self.job_started_event(job.child)
        self._dbg(1, 'Job "%s" started.' % job.name)

    def get_queue_length(self):
        return len(self.collection)

    def _on_job_completed(self, job, exc_info):
        # This function is called in a sub-thread, so we need to be
        # careful that we are not in a lock while sending an event.
        self._dbg(1, 'Job "%s" called completed()' % job.name)

        try:
            # Notify listeners of the error
            # *before* removing the job from the queue.
            # This is because wait_until_done() depends on
            # get_queue_length() being 0, and we don't want a listener
            # to get a signal from a queue that already already had
            # wait_until_done() completed.
            if exc_info:
                self._dbg(1, 'Error in job "%s"' % job.name)
                job.child.failures += 1
                self.job_error_event(job.child, exc_info)
                if job.child.failures >= job.child.times:
                    self._dbg(1, 'Job "%s" finally failed' % job.name)
                    self.job_aborted_event(job.child)
            else:
                self._dbg(1, 'Job "%s" succeeded.' % job.name)
                self.job_succeeded_event(job.child)

        finally:
            # Remove the watcher from the queue, and re-enque if needed.
            if exc_info and job.child.failures < job.child.times:
                self._dbg(1, 'Restarting job "%s"' % job.name)
                new_job = copy(job)
                self.collection.replace(job, new_job)
                self._start_job(new_job, False)
            else:
                self.collection.task_done(job)
                new_job = None

        if new_job:
            self.job_started_event(new_job.child)

    def run(self):
        self.collection.pause()
        while True:
            # Get the next job from the queue. This blocks until a task
            # is available (or until self.collection.stop() is called, which
            # is what we do in shutdown()).
            job = self.collection.next()
            if len(self.collection) <= 0:
                self.queue_empty_event()
            if job is None:
                break  # self.collection.stop() was called.

            self._start_job(job)
        self._dbg(2, 'Main loop terminated.')
