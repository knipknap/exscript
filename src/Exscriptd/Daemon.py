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
from threading import Thread
from Exscript.util.event import Event

class Daemon(object):
    def __init__(self, parent, name, logger):
        self.parent               = parent
        self.name                 = name
        self.logger               = logger
        self.order_incoming_event = Event()
        self.parent.daemon_added(self)

    def log(self, order, message, level = logging.INFO):
        msg = '%s/%s/%s: %s' % (self.name,
                                order.get_service_name(),
                                order.get_id(),
                                message)
        self.logger.log(level, msg)
