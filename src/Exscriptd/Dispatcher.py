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
import logging
from functools import partial
from collections import defaultdict
from threading import Thread, Lock
from Exscriptd.util import synchronized
from Exscriptd import Task

class _AsyncFunction(Thread):
    def __init__ (self, function, *args, **kwargs):
        Thread.__init__(self)
        self.function = function
        self.args     = args
        self.kwargs   = kwargs

    def run(self):
        self.function(*self.args, **self.kwargs)

class Dispatcher(object):
    def __init__(self, order_db, queues, logger, logdir):
        self.order_db = order_db
        self.queues   = {}
        self.logger   = logger
        self.loggers  = defaultdict(list) # map order id to loggers
        self.logdir   = logdir
        self.lock     = Lock()
        self.services = {}
        self.daemons  = {}
        self.logger.info('Closing all open orders.')
        self.order_db.close_open_orders()

        if not os.path.isdir(logdir):
            os.makedirs(logdir)
        for name, queue in queues.iteritems():
            self.add_queue(name, queue)

    def get_queue_from_name(self, name):
        return self.queues[name]

    def add_queue(self, name, queue):
        self.queues[name] = queue
        wq = queue.workqueue
        wq.job_init_event.connect(partial(self._on_job_event, name, 'init'))
        wq.job_started_event.connect(partial(self._on_job_event,
                                             name,
                                             'started'))
        wq.job_error_event.connect(partial(self._on_job_event,
                                           name,
                                           'error'))
        wq.job_succeeded_event.connect(partial(self._on_job_event,
                                               name,
                                               'succeeded'))
        wq.job_aborted_event.connect(partial(self._on_job_event,
                                             name,
                                             'aborted'))

    def _set_task_status(self, job_id, queue_name, status):
        # Log the status change.
        task = self.order_db.get_task(job_id = job_id)
        msg  = '%s/%s: %s' % (queue_name, job_id, status)
        if task is None:
            self.logger.info(msg + ' (untracked)')
            return
        self.logger.info(msg + ' (order id ' + str(task.order_id) + ')')

        # Update the task in the database.
        if status == 'succeeded':
            task.completed()
        elif status == 'started':
            task.set_status('running')
        elif status == 'aborted':
            task.close(status)
        else:
            task.set_status(status)
        self.order_db.save_task(task)

        # Check whether the order can now be closed.
        if task.get_closed_timestamp() is not None:
            order = self.order_db.get_order(id = task.order_id)
            self._update_order_status(order)

    def _on_job_event(self, queue_name, status, job, *args):
        self._set_task_status(job.id, queue_name, status)

    def set_job_name(self, job_id, name):
        task = self.order_db.get_task(job_id = job_id)
        task.set_name(name)
        self.order_db.save_task(task)

    def set_job_progress(self, job_id, progress):
        task = self.order_db.get_task(job_id = job_id)
        task.set_progress(progress)
        self.order_db.save_task(task)

    def get_order_logdir(self, order):
        orders_logdir = os.path.join(self.logdir, 'orders')
        order_logdir  = os.path.join(orders_logdir, str(order.get_id()))
        if not os.path.isdir(order_logdir):
            os.makedirs(order_logdir)
        return order_logdir

    def get_logger(self, order, name, level = logging.INFO):
        """
        Creates a logger that logs to a file in the order's log directory.
        """
        order_logdir = self.get_order_logdir(order)
        logfile      = os.path.join(order_logdir, name)
        logger       = logging.getLogger(logfile)
        handler      = logging.FileHandler(logfile)
        format       = r'%(asctime)s - %(levelname)s - %(message)s'
        formatter    = logging.Formatter(format)
        logger.setLevel(logging.INFO)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        self.loggers[order.get_id()].append(logger)
        return logger

    def _free_logger(self, logger):
        # hack to work around the fact that Python's logging module
        # provides no documented way to delete loggers.
        del logger.manager.loggerDict[logger.name]
        logger.manager = None

    def service_added(self, service):
        """
        Called by a service when it is initialized.
        """
        service.parent = self
        self.services[service.name] = service

    def daemon_added(self, daemon):
        """
        Called by a daemon when it is initialized.
        """
        daemon.parent = self
        self.daemons[daemon.name] = daemon
        daemon.order_incoming_event.listen(self.place_order, daemon.name)

    def log(self, order, message):
        msg = '%s/%s: %s' % (order.get_service_name(),
                             order.get_id(),
                             message)
        self.logger.info(msg)

    def get_order_db(self):
        return self.order_db

    def _update_order_status(self, order):
        remaining = self.order_db.count_tasks(order_id = order.id,
                                              closed   = None)
        if remaining == 0:
            total = self.order_db.count_tasks(order_id = order.id)
            if total == 1:
                task = self.order_db.get_task(order_id = order.id)
                order.set_description(task.get_name())
            order.close()
            self.set_order_status(order, 'completed')
            for logger in self.loggers.pop(order.get_id(), []):
                self._free_logger(logger)

    def _on_task_changed(self, task):
        self.order_db.save_task(task)

    def create_task(self, order, name):
        task = Task(order.id, name)
        task.changed_event.listen(self._on_task_changed)
        self.order_db.save_task(task)
        return task

    def set_order_status(self, order, status):
        order.status = status
        self.order_db.save_order(order)
        self.log(order, 'Status is now "%s"' % status)

    def place_order(self, order, daemon_name):
        self.logger.debug('Incoming order from ' + daemon_name)

        # Store it in the database.
        self.set_order_status(order, 'incoming')

        # Loop the requested service up.
        service = self.services.get(order.get_service_name())
        if not service:
            order.close()
            self.set_order_status(order, 'service-not-found')
            return

        # Notify the service of the new order.
        try:
            accepted = service.check(order)
        except Exception, e:
            self.log(order, 'Exception: %s' % e)
            order.close()
            self.set_order_status(order, 'error')
            raise

        if not accepted:
            order.close()
            self.set_order_status(order, 'rejected')
            return
        self.set_order_status(order, 'accepted')

        # Save the order, including the data that was passed.
        # For performance reasons, use a new thread.
        func = _AsyncFunction(self._enter_order, service, order)
        func.start()

    def _enter_order(self, service, order):
        # Note: This method is called asynchronously.
        # Store the order in the database.
        self.set_order_status(order, 'saving')
        self.order_db.save_order(order)

        self.set_order_status(order, 'starting')
        with self.lock:
            # We must stop the queue while new jobs are placed,
            # else the queue might start processing a job before
            # it was attached to a task.
            for queue in self.queues.itervalues():
                queue.workqueue.pause()

            try:
                service.enter(order)
            except Exception, e:
                self.log(order, 'Exception: %s' % e)
                order.close()
                self.set_order_status(order, 'error')
                raise
            finally:
                # Re-enable the workqueue.
                for queue in self.queues.itervalues():
                    queue.workqueue.unpause()
        self.set_order_status(order, 'running')

        # If the service did not enqueue anything, it may already be completed.
        self._update_order_status(order)
