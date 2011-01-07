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
import os, logging
from collections             import defaultdict
from threading               import Lock
from Exscriptd               import Task
from ConfigReader            import ConfigReader
from Exscript.util.decorator import bind

class Service(object):
    def __init__(self,
                 daemon,
                 name,
                 cfg_dir,
                 main_cfg,
                 queue = None):
        self.main_cfg  = main_cfg
        self.cfg_dir   = cfg_dir
        self.daemon    = daemon
        self.name      = name
        self.queue     = queue
        self.task_lock = Lock()
        self.tasks     = defaultdict(list) # Map order ids to lists of tasks.
        self.loggers   = defaultdict(list) # Map order ids to loggers.

    def log(self, order, message):
        self.daemon.log(order, message)

    def get_logname(self, order, name = ''):
        return os.path.join(self.daemon.get_logdir(),
                            self.name,
                            str(order.get_id()),
                            name)

    def create_logger(self, order, name, level = logging.INFO):
        logfile   = self.get_logname(order, name)
        logger    = logging.getLogger(logfile)
        handler   = logging.FileHandler(logfile)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        logger.setLevel(logging.INFO)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        self.loggers[order.id].append(logger)
        return logger

    def _free_loggers(self, order):
        for logger in self.loggers[order.id]:
            del logger.manager.loggerDict[logger.name]
            logger.manager = None
        del self.loggers[order.id]

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
            task.done_event.connect(self._task_done, order, task)
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
        for host in hosts:
            self._update_host_logname(order, host)

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
        for host in hosts:
            self._update_host_logname(order, host)

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
        self._free_loggers(order)
        self.daemon.set_order_status_done(order)

    def set_order_status(self, order, status):
        self.daemon.set_order_status(order, status)

    def save_order(self, order):
        self.daemon.save_order(order)

    def create_task(self, order, name):
        task = Task(name)
        self.save_task(order, task)
        return task

    def save_task(self, order, task):
        self.daemon.save_task(order, task)
