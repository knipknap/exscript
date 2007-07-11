# Copyright (C) 2007 Samuel Abels, http://debain.org
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
import threading
import time
from Job import Job

True  = 1
False = 0

class MainLoop(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.queue               = []
        self.running_jobs        = []
        self.paused              = True
        self.shutdown_now        = False
        self.max_threads         = 1
        self.global_context      = {}
        self.global_context_lock = threading.Lock()
        self.debug               = 0
        self.setDaemon(1)

    def set_max_threads(self, max_threads):
        assert max_threads is not None
        self.max_threads = max_threads

    def enqueue(self, action):
        self.queue.append(action)

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def is_paused(self):
        return self.paused

    def shutdown(self):
        self.shutdown_now = True
        for job in self.running_jobs:
            job.join()
            print 'Job "%s" finished' % job.getName()

    def get_queue_length(self):
        #print "Queue length:", len(self.queue)
        return len(self.queue) + len(self.running_jobs)

    def run(self):
        while not self.shutdown_now:
            # Join any finished threads.
            running_jobs = []
            for job in self.running_jobs:
                if job.isAlive():
                    running_jobs.append(job)
                    continue
                print 'Job "%s" finished' % job.getName()
                job.join()
            self.running_jobs = running_jobs[:]

            # Don't bother looking if the queue is empty.
            if len(self.queue) <= 0 or self.paused:
                time.sleep(1)
                continue

            # Wait until we have less than the maximum number of threads.
            if len(self.running_jobs) >= self.max_threads:
                #print 'Maximum number of threads running, waiting...'
                time.sleep(1)
                continue

            # Take the next action and start it in a new thread.
            action    = self.queue.pop(0)
            n_threads = len(self.running_jobs)
            job       = Job(self.global_context_lock,
                            self.global_context,
                            action,
                            debug = self.debug)
            job.start()
            self.running_jobs.append(job)
            print 'Job "%s" started.' % job.getName()

            if len(self.queue) <= 0:
                print 'No more pending actions in the queue.'
        print 'Main loop terminated.'
