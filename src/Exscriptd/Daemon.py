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
import os, logging, logging.handlers
from lxml                    import etree
from Order                   import Order
from Exscript                import Host
from Exscript.util.decorator import bind

# Logfile structure:
# /var/log/exscriptd/mydaemon/access.log
# /var/log/exscriptd/mydaemon/myservice/123/host2.log
# /var/log/exscriptd/mydaemon/myservice/123/host3.log

class Daemon(object):
    def __init__(self,
                 name,
                 database   = None,
                 processors = None,
                 logdir     = None):
        self.name       = name
        self.db         = database
        self.processors = processors
        self.services   = {}
        self.logdir     = os.path.join(logdir, name)
        self.logger     = logging.getLogger('exscriptd_' + name)
        self.logger.setLevel(logging.INFO)
        if not os.path.isdir(self.logdir):
            os.makedirs(self.logdir)

        # Set up logfile rotation.
        logfile = os.path.join(self.logdir, 'access.log')
        handler = logging.handlers.RotatingFileHandler(logfile,
                                                       maxBytes    = 200000,
                                                       backupCount = 5)

        # Define the log format.
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def log(self, order, message):
        msg = '%s/%s/%s: %s' % (self.name,
                                order.get_service_name(),
                                order.get_id(),
                                message)
        self.logger.info(msg)

    def get_logdir(self):
        return self.logdir

    def add_service(self, name, service):
        self.services[name] = service

    def get_order_from_id(self, order_id):
        return self.db.get_order(id = order_id)

    def set_order_status(self, order, status):
        order.status = status
        self.db.save_order(order, recursive = False)
        self.log(order, 'Status is now "%s"' % status)

    def set_order_status_done(self, order):
        self.set_order_status(order, 'completed')

    def save_order(self, order):
        return self.db.save_order(order)

    def _place_order(self, order):
        # Store it in the database.
        self.set_order_status(order, 'incoming')

        # Loop the requested service up.
        service = self.services.get(order.service)
        if not service:
            self.set_order_status(order, 'service-not-found')
            return

        # Create the log directory.
        os.makedirs(service.get_logname(order))

        # Notify the service of the new order.
        try:
            accepted = service.enter(order)
        except Exception, e:
            self.log(order, 'Exception: %s' % e)
            self.set_order_status(order, 'error')
            raise

        if not accepted:
            self.set_order_status(order, 'rejected')
            return

        # Save the order, including the data that was passed.
        order.status = 'accepted'
        self.db.save_order(order)
