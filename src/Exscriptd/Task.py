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
"""
Represents an activity within an order.
"""
from datetime import datetime
from lxml     import etree
from DBObject import DBObject

class Task(DBObject):
    def __init__(self, name):
        DBObject.__init__(self)
        self.id       = None
        self.name     = name
        self.status   = 'new'
        self.progress = .0
        self.started  = datetime.utcnow()
        self.closed   = None

    @staticmethod
    def from_etree(task_node):
        """
        Creates a new instance by parsing the given XML.

        @type  task_node: lxml.etree.Element
        @param task_node: The task node of an etree.
        @rtype:  Task
        @return: A new instance of an task.
        """
        # Parse required attributes.
        name          = task_node.find('name').text
        task          = Task(name)
        task.id       = int(task_node.get('id'))
        task.status   = task_node.find('status').text
        task.progress = float(task_node.find('progress').text)
        started_node  = task_node.find('started')
        closed_node   = task_node.find('closed')
        if started_node is not None:
            started = started_node.text.split('.', 1)[0]
            started = datetime.strptime(started, "%Y-%m-%d %H:%M:%S")
            task.started = started
        if closed_node is not None:
            closed = closed_node.text.split('.', 1)[0]
            closed = datetime.strptime(closed, "%Y-%m-%d %H:%M:%S")
            task.closed = closed
        return task

    def toetree(self):
        """
        Returns the task as an lxml etree.

        @rtype:  lxml.etree
        @return: The resulting tree.
        """
        task = etree.Element('task', id = str(self.id))
        etree.SubElement(task, 'name').text     = str(self.name)
        etree.SubElement(task, 'status').text   = str(self.status)
        etree.SubElement(task, 'progress').text = str(self.progress)
        if self.started:
            etree.SubElement(task, 'started').text = str(self.started)
        if self.closed:
            etree.SubElement(task, 'closed').text = str(self.closed)
        return task

    def todict(self):
        return dict(name     = self.get_name(),
                    status   = self.get_status(),
                    progress = self.get_progress(),
                    started  = self.get_started_timestamp(),
                    closed   = self.get_closed_timestamp())

    def get_id(self):
        """
        Returns the task id.

        @rtype:  str
        @return: The id of the task.
        """
        return self.id

    def set_name(self, name):
        """
        Change the task name.

        @type  name: string
        @param name: A human readable name.
        """
        self.touch()
        self.name = name

    def get_name(self):
        """
        Returns the current name as a string.

        @rtype:  string
        @return: A human readable name.
        """
        return self.name

    def set_status(self, status):
        """
        Change the current status.

        @type  status: string
        @param status: A human readable status.
        """
        self.touch()
        self.status = status

    def get_status(self):
        """
        Returns the current status as a string.

        @rtype:  string
        @return: A human readable status.
        """
        return self.status

    def set_progress(self, progress):
        """
        Change the current progress.

        @type  progress: float
        @param progress: The new progress.
        """
        self.touch()
        self.progress = progress

    def get_progress(self):
        """
        Returns the progress as a float between 0.0 and 1.0.

        @rtype:  float
        @return: The progress.
        """
        return self.progress

    def get_progress_percent(self):
        """
        Returns the progress as a float between 0.0 and 100.0.

        @rtype:  float
        @return: The progress in percent.
        """
        return '%.1f' % (self.progress * 100.0)

    def get_started_timestamp(self):
        """
        Returns the time at which the task was started.

        @rtype:  datetime.datetime
        @return: The timestamp.
        """
        return self.started

    def close(self, status = None):
        """
        Marks the task closed.

        @type  status: string
        @param status: A human readable status, or None to leave unchanged.
        """
        self.touch()
        self.closed = datetime.utcnow()
        if status:
            self.set_status(status)

    def completed(self):
        """
        Like close(), but sets the status to 'completed' and the progress
        to 100%.
        """
        self.close('completed')
        self.set_progress(1.0)

    def get_closed_timestamp(self):
        """
        Returns the time at which the task was closed, or None if the
        task is still open.

        @rtype:  datetime.datetime|None
        @return: The timestamp or None.
        """
        return self.closed
