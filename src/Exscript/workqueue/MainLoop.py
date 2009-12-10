# Copyright (C) 2007-2009 Samuel Abels.
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
import threading, time, gc
from Exscript.external.SpiffSignal import Trackable
from Job                           import Job

True  = 1
False = 0

class MainLoop(Trackable, threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        Trackable.__init__(self)
        self.queue        = []
        self.force_start  = []
        self.running_jobs = []
        self.paused       = True
        self.shutdown_now = False
        self.max_threads  = 1
        self.condition    = threading.Condition()
        self.debug        = 0
        self.setDaemon(1)

    def _dbg(self, level, msg):
        if self.debug >= level:
            print msg

    def get_max_threads(self):
        return self.max_threads

    def set_max_threads(self, max_threads):
        assert max_threads is not None
        self.condition.acquire()
        self.max_threads = max_threads
        self.condition.notify_all()
        self.condition.release()

    def enqueue(self, action):
        self.condition.acquire()
        self.queue.append(action)
        self.condition.notify_all()
        self.condition.release()

    def priority_enqueue(self, action, force_start = False):
        self.condition.acquire()
        if force_start:
            self.force_start.append(action)
        else:
            self.queue.insert(0, action)
        self.condition.notify_all()
        self.condition.release()

    def pause(self):
        self.condition.acquire()
        self.paused = True
        self.condition.notify_all()
        self.condition.release()

    def resume(self):
        self.condition.acquire()
        self.paused = False
        self.condition.notify_all()
        self.condition.release()

    def is_paused(self):
        return self.paused

    def wait_for(self, action):
        self.condition.acquire()
        while self.in_queue(action):
            self.condition.wait()
        self.condition.release()

    def wait_for_activity(self):
        self.condition.acquire()
        self.condition.wait(.2)
        self.condition.release()

    def wait_until_done(self):
        self.condition.acquire()
        while self.get_queue_length() > 0:
            self.condition.wait()
        self.condition.release()

    def shutdown(self):
        self.condition.acquire()
        self.shutdown_now = True
        self.condition.notify_all()
        self.condition.release()
        for job in self.running_jobs:
            job.join()
            self._dbg(1, 'Job "%s" finished' % job.getName())

    def in_queue(self, action):
        return action in self.queue \
            or action in self.force_start \
            or self.in_progress(action)

    def in_progress(self, action):
        return action in self.get_running_actions()

    def get_running_actions(self):
        return [job.action for job in self.running_jobs]

    def get_queue_length(self):
        #print "Queue length:", len(self.queue)
        return len(self.queue) + len(self.running_jobs)

    def _start_action(self, action):
        job = Job(self.condition, action, debug = self.debug)
        self.running_jobs.append(job)
        job.start()
        self._dbg(1, 'Job "%s" started.' % job.getName())
        try:
            self.signal_emit('job-started', job)
        except:
            pass

    def _on_job_completed(self, job):
        try:
            if job.exception:
                self._dbg(1, 'Job "%s" aborted.' % job.getName())
                self.signal_emit('job-aborted', job, job.exception)
            else:
                self._dbg(1, 'Job "%s" succeeded.' % job.getName())
                self.signal_emit('job-succeeded', job)
        except:
            pass
        try:
            self.signal_emit('job-completed', job)
        except:
            pass

    def _update_running_jobs(self):
        running_jobs = []
        for job in self.running_jobs:
            if job.is_alive():
                running_jobs.append(job)
                continue
            self._on_job_completed(job)
            job.join()
            del job
        self.running_jobs = running_jobs[:]
        gc.collect()

    def run(self):
        self.condition.acquire()
        while not self.shutdown_now:
            self._update_running_jobs()

            # If there are any actions to be force_started, run them now.
            for action in self.force_start:
                self._start_action(action)
            self.force_start = []
            self.condition.notify_all()

            # Don't bother looking if the queue is empty.
            if len(self.queue) <= 0 or self.paused:
                self.condition.wait()
                continue

            # Wait until we have less than the maximum number of threads.
            if len(self.running_jobs) >= self.max_threads:
                self.condition.wait()
                continue

            # Take the next action and start it in a new thread.
            action = self.queue.pop(0)
            self._start_action(action)
            self.condition.release()

            if len(self.queue) <= 0:
                self._dbg(2, 'No more pending actions in the queue.')
            self.condition.acquire()
        self.condition.release()
        self._dbg(2, 'Main loop terminated.')
