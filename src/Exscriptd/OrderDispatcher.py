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
from collections import defaultdict
from threading import Thread

class _AsyncFunction(Thread):
    def __init__ (self, function, *args, **kwargs):
        Thread.__init__(self)
        self.function = function
        self.args     = args
        self.kwargs   = kwargs

    def run(self):
        self.function(*self.args, **self.kwargs)

class OrderDispatcher(object):
    def __init__(self, order_db, queues, logger, logdir):
        self.order_db = order_db
        self.queues   = queues
        self.logger   = logger
        self.logdir   = logdir
        self.services = {}
        self.daemons  = {}
        self.loggers  = defaultdict(dict) # Map order id to name/logger pairs.
        self.logger.info('Closing all open orders.')
        self.order_db.close_open_orders()

    def get_logger(self, order, name, level = logging.INFO):
        """
        Creates a logger that logs to a file in the order's log directory.
        """
        if name in self.loggers[order.id]:
            return self.loggers[order.id][name]
        service_logdir = os.path.join(self.logdir, order.get_service_name())
        order_logdir   = os.path.join(service_logdir, str(order.get_id()))
        logfile        = os.path.join(order_logdir, name)
        logger         = logging.getLogger(logfile)
        handler        = logging.FileHandler(logfile)
        format         = r'%(asctime)s - %(levelname)s - %(message)s'
        formatter      = logging.Formatter(format)
        logger.setLevel(logging.INFO)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        self.loggers[order.id][name] = logger
        return logger

    def _free_loggers(self, order):
        for logger in self.loggers[order.id]:
            # hack to work around the fact that Python's logging module
            # provides no documented way to delete loggers.
            del logger.manager.loggerDict[logger.name]
            logger.manager = None
        del self.loggers[order.id]

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

    def set_order_status_done(self, order):
        order.close()
        self._free_loggers(order)
        self.set_order_status(order, 'completed')

    def _on_task_go(self, task, order):
        task.go_event.disconnect_all()
        task.changed_event.listen(self._on_task_changed, order)
        task.closed_event.listen(self._on_task_closed, order)

    def _on_task_changed(self, task, order):
        self.order_db.save_task(order, task)

    def _on_task_closed(self, task, order):
        task.go_event.disconnect_all()
        task.closed_event.disconnect_all()
        task.changed_event.disconnect_all()

    def create_task(self, order, name, queue_name, func):
        task = Task(name, queue_name, func)
        task.go_event.listen(self._on_task_go, order)
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

        # Create the log directory.
        os.makedirs(service.get_logname(order))

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

        self.set_order_status(order, 'enter-start')
        try:
            result = service.enter(order)
        except Exception, e:
            self.log(order, 'Exception: %s' % e)
            order.close()
            self.set_order_status(order, 'enter-exception')
            raise

        if not result:
            self.log(order, 'Error: enter() returned False')
            order.close()
            self.set_order_status(order, 'enter-error')
            return
        self.set_order_status(order, 'entered')

        # If the service did not enqueue anything, it also
        # has no opportunity to mark the order 'done'. So mark
        # it automatically here.
        service._enter_completed_notify(order)
