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
from multiprocessing import Pipe
from itertools import chain
from collections import defaultdict, deque
from Exscript.util.event import Event
from Exscript.workqueue.Job import Job

class _ChildWatcher(threading.Thread):
    def __init__(self, child, callback):
        threading.Thread.__init__(self)
        self.child = child
        self.cb    = callback

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
            self.cb(self.child, None)
        else:
            self.cb(self.child, result)

class MainLoop(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.job_init_event      = Event()
        self.job_started_event   = Event()
        self.job_error_event     = Event()
        self.job_succeeded_event = Event()
        self.job_aborted_event   = Event()
        self.queue_empty_event   = Event()
        self.queue               = deque()
        self.force_start         = []
        self.running_jobs        = []
        self.sleeping_jobs       = set()
        self.watchers            = {}
        self.paused              = True
        self.shutdown_now        = False
        self.max_threads         = 1
        self.condition           = threading.Condition()
        self.debug               = 5
        self.daemon              = True

    def _dbg(self, level, msg):
        if self.debug >= level:
            print msg

    def _job_sleep_notify(self, job):
        assert job in self.running_jobs
        with self.condition:
            self.sleeping_jobs.add(job)
            self.condition.notify_all()

    def _job_wake_notify(self, job):
        assert job in self.running_jobs
        assert job in self.sleeping_jobs
        with self.condition:
            self.sleeping_jobs.remove(job)
            self.condition.notify_all()

    def get_max_threads(self):
        return self.max_threads

    def set_max_threads(self, max_threads):
        assert max_threads is not None
        with self.condition:
            self.max_threads = int(max_threads)
            self.condition.notify_all()

    def _create_job(self, function, name, times, data):
        if name is None:
            name = str(id(function))
        job = Job(function, name, times, data)
        self.job_init_event(job)
        return job

    def enqueue(self, function, name, times, data):
        with self.condition:
            job = self._create_job(function, name, times, data)
            self.queue.append(job)
            self.condition.notify_all()
        return id(job)

    def enqueue_or_ignore(self, function, name, times, data):
        with self.condition:
            job = None
            if self.get_first_job_from_name(name) is None:
                job = self._create_job(function, name, times, data)
                self.queue.append(job)
            self.condition.notify_all()
        return job is not None and id(job) or None

    def priority_enqueue(self, function, name, force_start, times, data):
        with self.condition:
            job = self._create_job(function, name, times, data)
            if force_start:
                self.force_start.append(job)
            else:
                self.queue.appendleft(job)
            self.condition.notify_all()
        return id(job)

    def priority_enqueue_or_raise(self,
                                  function,
                                  name,
                                  force_start,
                                  times,
                                  data):
        with self.condition:
            # If the job is already running (or about to be forced),
            # there is nothing to be done.
            for job in chain(self.force_start, self.running_jobs):
                if job.name == name:
                    self.condition.notify_all()
                    return None

            # If the job is already in the queue, remove it so we can
            # re-add it at the top of the queue later.
            existing_job = None
            for job in self.queue:
                if job.name == name:
                    existing_job = job
                    self.queue.remove(existing_job)
                    break

            # If it was not in the queue, create a new job.
            if existing_job is None:
                job = self._create_job(function, name, times, data)
            else:
                job = existing_job

            # Now insert the job into the queue.
            if force_start:
                self.force_start.append(job)
            else:
                self.queue.appendleft(job)
            self.condition.notify_all()
        return existing_job is None and id(job) or None

    def pause(self):
        with self.condition:
            self.paused = True
            self.condition.notify_all()

    def resume(self):
        with self.condition:
            self.paused = False
            self.condition.notify_all()

    def is_paused(self):
        return self.paused

    def _get_job_from_id(self, job_id):
        for job in chain(self.queue, self.force_start, self.running_jobs):
            if id(job) == job_id:
                return job
        return None

    def wait_for(self, job_id):
        with self.condition:
            while self._get_job_from_id(job_id) is not None:
                self.condition.wait()
                continue
            watcher = self.watchers.get(job_id)
            if watcher is not None:
                watcher.join()

    def wait_for_activity(self):
        with self.condition:
            self.condition.wait(.2)

    def _wait_for_watchers(self):
        for watcher in self.watchers.values():
            watcher.join()
            self._dbg(1, 'Watcher for "%s" joined' % watcher.child.name)

    def wait_until_done(self):
        with self.condition:
            while self.get_queue_length() > 0:
                self.condition.wait()
        self._wait_for_watchers()

    def shutdown(self):
        with self.condition:
            self.shutdown_now = True
            self.condition.notify_all()
        self._wait_for_watchers()

    def _job_in_queue(self, job):
        return job in self.queue or \
               job in self.force_start or \
               job in self.running_jobs

    def get_queue_length(self):
        return len(self.queue) \
             + len(self.force_start) \
             + len(self.running_jobs)

    def get_first_job_from_name(self, job_name):
        if job_name is None:
            return None
        for job in chain(self.queue, self.force_start, self.running_jobs):
            if job.name == job_name:
                return job
        return None

    def _start_job(self, job):
        self.running_jobs.append(job)
        self.job_started_event(job)
        watcher = _ChildWatcher(job, self._on_job_completed)
        self.watchers[id(job)] = watcher
        watcher.start()
        self._dbg(1, 'Job "%s" started.' % job.name)

    def _restart_job(self, job):
        self._start_job(copy(job))

    def _on_job_completed(self, job, exc_info):
        self._dbg(1, 'Job "%s" called completed()' % job.name)
        with self.condition:
            self.running_jobs.remove(job)
            self.condition.notify_all()

        if exc_info:
            self._dbg(1, 'Error in job "%s"' % job.name)
            job.failures += 1
            self.job_error_event(job, exc_info)
            if job.failures >= job.times:
                self._dbg(1, 'Job "%s" finally failed' % job.name)
                self.job_aborted_event(job)
            else:
                self._dbg(1, 'Restarting job "%s"' % job.name)
                self._restart_job(job)
        else:
            self._dbg(1, 'Job "%s" succeeded.' % job.name)
            self.job_succeeded_event(job)

        self.watchers.pop(id(job))

    def run(self):
        self.condition.acquire()
        while not self.shutdown_now:
            if self.get_queue_length() == 0:
                self.queue_empty_event()

            # If there are any jobs to be force_started, run them now.
            for job in self.force_start:
                self._start_job(job)
            self.force_start = []
            self.condition.notify_all()

            # Don't bother looking if the queue is empty.
            if len(self.queue) <= 0 or self.paused:
                self.condition.wait()
                continue

            # Wait until we have less than the maximum number of threads.
            active = len(self.running_jobs) - len(self.sleeping_jobs)
            if active >= self.max_threads:
                self.condition.wait()
                continue

            # Take the next job and start it in a new thread.
            job = self.queue.popleft()
            self._start_job(job)
            self.condition.release()

            if len(self.queue) <= 0:
                self._dbg(2, 'No more pending jobs in the queue.')
            self.condition.acquire()
        self.condition.release()
        self._dbg(2, 'Main loop terminated.')
