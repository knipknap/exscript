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
import threading
import gc
from itertools              import chain
from collections            import defaultdict, deque
from Exscript.util.event    import Event
from Exscript.workqueue.Job import Job

class MainLoop(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.job_started_event   = Event()
        self.job_succeeded_event = Event()
        self.job_aborted_event   = Event()
        self.job_completed_event = Event()
        self.queue_empty_event   = Event()
        self.queue               = deque()
        self.force_start         = []
        self.running_jobs        = []
        self.sleeping_actions    = []
        self.paused              = True
        self.shutdown_now        = False
        self.max_threads         = 1
        self.condition           = threading.Condition()
        self.debug               = 0
        self.daemon              = True

    def _dbg(self, level, msg):
        if self.debug >= level:
            print msg

    def _action_sleep_notify(self, action):
        assert self.in_progress(action)
        with self.condition:
            self.sleeping_actions.append(action)
            self.condition.notify_all()

    def _action_wake_notify(self, action):
        assert self.in_progress(action)
        assert action in self.sleeping_actions
        with self.condition:
            self.sleeping_actions.remove(action)
            self.condition.notify_all()

    def get_max_threads(self):
        return self.max_threads

    def set_max_threads(self, max_threads):
        assert max_threads is not None
        with self.condition:
            self.max_threads = int(max_threads)
            self.condition.notify_all()

    def enqueue(self, action):
        with self.condition:
            self.queue.append(action)
            self.condition.notify_all()

    def enqueue_or_ignore(self, action):
        with self.condition:
            if not self.get_first_action_from_name(action.name):
                self.queue.append(action)
                enqueued = True
            else:
                enqueued = False
            self.condition.notify_all()
        return enqueued

    def priority_enqueue(self, action, force_start = False):
        with self.condition:
            if force_start:
                self.force_start.append(action)
            else:
                self.queue.appendleft(action)
            self.condition.notify_all()

    def priority_enqueue_or_raise(self, action, force_start = False):
        with self.condition:
            # If the action is already running (or about to be forced),
            # there is nothing to be done.
            running_actions = self.get_running_actions()
            for queue_action in chain(self.force_start, running_actions):
                if queue_action.name == action.name:
                    self.condition.notify_all()
                    return False

            # If the action is already in the queue, remove it so it can be
            # re-added later.
            existing = None
            for queue_action in self.queue:
                if queue_action.name == action.name:
                    existing = queue_action
                    break
            if existing:
                self.queue.remove(existing)
                action = existing

            # Now add the action to the queue.
            if force_start:
                self.force_start.append(action)
            else:
                self.queue.appendleft(action)

            self.condition.notify_all()
        return existing is None

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

    def _get_action_from_hash(self, thehash):
        for action in chain(self.queue, self.force_start):
            if action.__hash__() == thehash:
                return action
        for action in self.get_running_actions():
            if action.__hash__() == thehash:
                return action
        return None

    def wait_for(self, action):
        with self.condition:
            # If we were passed the hash of an action, look the action up
            # first.
            if isinstance(action, int):
                action = self._get_action_from_hash(action)
                if action is None:
                    return

            # Wait until the action completes.
            while self.in_queue(action):
                self.condition.wait()

    def wait_for_activity(self):
        with self.condition:
            self.condition.wait(.2)

    def wait_until_done(self):
        with self.condition:
            while self.get_queue_length() > 0:
                self.condition.wait()

    def shutdown(self):
        with self.condition:
            self.shutdown_now = True
            self.condition.notify_all()
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
        return len(self.queue) \
             + len(self.force_start) \
             + len(self.running_jobs)

    def get_actions_from_name(self, name):
        actions = self.queue + self.force_start + self.running_jobs
        map     = defaultdict(list)
        for action in self.get_running_actions():
            map[action.get_name()].append(action)
        return map[name]

    def get_first_action_from_name(self, action_name):
        for action in chain(self.queue, self.force_start, self.running_jobs):
            if action.name == action_name:
                return action
        return None

    def _start_action(self, action):
        action.debug = self.debug
        job          = Job(self.condition, action, action.name)
        self.running_jobs.append(job)
        job.start()
        self._dbg(1, 'Job "%s" started.' % job.getName())
        self.job_started_event(action)

    def _on_job_completed(self, job):
        if job.exception:
            self._dbg(1, 'Job "%s" aborted.' % job.getName())
            self.job_aborted_event(job.action, job.exception)
        else:
            self._dbg(1, 'Job "%s" succeeded.' % job.getName())
            self.job_succeeded_event(job.action)
        self.job_completed_event(job.action)

    def _update_running_jobs(self):
        # Update the list of running jobs.
        running   = []
        completed = []
        for job in self.running_jobs:
            if job.is_alive():
                running.append(job)
                continue
            completed.append(job)
        self.running_jobs = running[:]

        # Notify any clients *after* removing the job from the list.
        for job in completed:
            self._on_job_completed(job)
            job.join()
            del job
        gc.collect()

    def run(self):
        self.condition.acquire()
        while not self.shutdown_now:
            self._update_running_jobs()
            if self.get_queue_length() == 0:
                self.queue_empty_event()

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
            active = len(self.running_jobs) - len(self.sleeping_actions)
            if active >= self.max_threads:
                self.condition.wait()
                continue

            # Take the next action and start it in a new thread.
            action = self.queue.popleft()
            self._start_action(action)
            self.condition.release()

            if len(self.queue) <= 0:
                self._dbg(2, 'No more pending actions in the queue.')
            self.condition.acquire()
        self.condition.release()
        self._dbg(2, 'Main loop terminated.')
