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
import os
from collections            import defaultdict
from threading              import Lock
from Exscriptd.Task         import Task
from Exscriptd.ConfigReader import ConfigReader

class Service(object):
    def __init__(self,
                 parent,
                 name,
                 cfg_dir,
                 logdir,
                 main_cfg,
                 queue = None):
        self.parent    = parent
        self.name      = name
        self.cfg_dir   = cfg_dir
        self.logdir    = logdir
        self.main_cfg  = main_cfg
        self.queue     = queue
        self.logdir    = os.path.join(self.daemon.get_logdir(), name)
        self.task_lock = Lock()
        self.tasks     = defaultdict(list) # Map order ids to lists of tasks.
        self.parent.service_added(self)

    def log(self, order, message):
        self.parent.log(order, message)

    def get_logname(self, order, name = ''):
        return os.path.join(self.logdir, str(order.get_id()), name)

    def _update_host_logname(self, order, host):
        host.set_logname(self.get_logname(order, host.get_logname()))

    def config_file(self, name):
        return os.path.join(self.cfg_dir, name)

    def config(self, name, parser = ConfigReader):
        path = self.config_file(name)
        return parser(path, parent = self.main_cfg)

    def _track_task(self, order, task):
        if not task:
            return
        with self.task_lock:
            task.done_event.listen(self._task_done, order, task)
            self.tasks[order.id].append(task)

    def _task_done(self, order, task):
        with self.task_lock:
            if task is not None:
                self.tasks[order.id].remove(task)
            if not self.tasks[order.id]:
                del self.tasks[order.id]
                self.done(order)

    def _enter_completed_notify(self, order):
        self._task_done(order, None)

    def enqueue_hosts(self,
                      order,
                      hosts,
                      callback,
                      handle_duplicates = False):
        # For performance reasons, we defer the starting of further
        # threads by pausing the queue.
        # We also need to pause to avoid getting a 'done' signal before
        # the signal is connected.
        self.queue.workqueue.pause()
        if handle_duplicates:
            task = self.queue.run_or_ignore(hosts, callback)
        else:
            task = self.queue.run(hosts, callback)
        self._track_task(order, task)
        self.queue.workqueue.unpause()
        return task

    def priority_enqueue_hosts(self,
                               order,
                               hosts,
                               callback,
                               handle_duplicates = False):
        self.queue.workqueue.pause()
        if handle_duplicates:
            task = self.queue.priority_run_or_raise(hosts, callback)
        else:
            task = self.queue.priority_run(hosts, callback)
        self._track_task(order, task)
        self.queue.workqueue.unpause()
        return task

    def enqueue(self, order, function, name):
        name = self.get_logname(order, name)
        self.queue.workqueue.pause()
        task = self.queue.enqueue(function, name)
        self._track_task(order, task)
        self.queue.workqueue.unpause()
        return task

    def check(self, order):
        return True

    def enter(self, order):
        return True

    def done(self, order):
        self.parent.set_order_status_done(order)

    def set_order_status(self, order, status):
        self.parent.set_order_status(order, status)

    def save_order(self, order):
        self.parent.save_order(order)

    def create_task(self, order, name):
        task = Task(name)
        self.save_task(order, task)
        return task

    def save_task(self, order, task):
        self.parent.save_task(order, task)
