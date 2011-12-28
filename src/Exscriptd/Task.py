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
import os
import sys
from datetime import datetime
from lxml import etree
from Exscriptd.DBObject import DBObject
from Exscript.util.event import Event

class Task(DBObject):
    def __init__(self, order_id, name):
        DBObject.__init__(self)
        self.id            = None
        self.order_id      = order_id
        self.job_id        = None   # reference to Exscript.workqueue.Job.id
        self.name          = name
        self.status        = 'new'
        self.progress      = .0
        self.started       = datetime.utcnow()
        self.closed        = None
        self.logfile       = None
        self.tracefile     = None
        self.vars          = {}
        self.changed_event = Event()

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
        name           = task_node.find('name').text
        order_id       = task_node.get('order_id')
        task           = Task(order_id, name)
        task.id        = int(task_node.get('id'))
        task.status    = task_node.find('status').text
        task.progress  = float(task_node.find('progress').text)
        started_node   = task_node.find('started')
        closed_node    = task_node.find('closed')
        logfile_node   = task_node.find('logfile')
        tracefile_node = task_node.find('tracefile')
        if started_node is not None:
            started = started_node.text.split('.', 1)[0]
            started = datetime.strptime(started, "%Y-%m-%d %H:%M:%S")
            task.started = started
        if closed_node is not None:
            closed = closed_node.text.split('.', 1)[0]
            closed = datetime.strptime(closed, "%Y-%m-%d %H:%M:%S")
            task.closed = closed
        if logfile_node is not None:
            task.logfile = logfile_node.text
        if tracefile_node is not None:
            task.tracefile = tracefile_node.text
        return task

    @staticmethod
    def from_xml(xml):
        """
        Creates a new instance by parsing the given XML.

        @type  xml: str
        @param xml: A string containing an XML formatted task.
        @rtype:  Task
        @return: A new instance of an task.
        """
        xml = etree.fromstring(xml)
        return Task.from_etree(xml.find('task'))

    def toetree(self):
        """
        Returns the task as an lxml etree.

        @rtype:  lxml.etree
        @return: The resulting tree.
        """
        task = etree.Element('task',
                             id       = str(self.id),
                             order_id = str(self.order_id))
        etree.SubElement(task, 'name').text     = str(self.name)
        etree.SubElement(task, 'status').text   = str(self.status)
        etree.SubElement(task, 'progress').text = str(self.progress)
        if self.started:
            etree.SubElement(task, 'started').text = str(self.started)
        if self.closed:
            etree.SubElement(task, 'closed').text = str(self.closed)
        if self.logfile:
            etree.SubElement(task, 'logfile').text = str(self.logfile)
        if self.tracefile:
            etree.SubElement(task, 'tracefile').text = str(self.tracefile)
        return task

    def toxml(self, pretty = True):
        """
        Returns the task as an XML formatted string.

        @type  pretty: bool
        @param pretty: Whether to format the XML in a human readable way.
        @rtype:  str
        @return: The XML representing the task.
        """
        xml  = etree.Element('xml')
        task = self.toetree()
        xml.append(task)
        return etree.tostring(xml, pretty_print = pretty)

    def todict(self):
        result = dict(order_id  = self.order_id,
                      job_id    = self.get_job_id(),
                      name      = self.get_name(),
                      status    = self.get_status(),
                      progress  = self.get_progress(),
                      started   = self.get_started_timestamp(),
                      closed    = self.get_closed_timestamp(),
                      logfile   = self.get_logfile(),
                      tracefile = self.get_tracefile(),
                      vars      = self.vars)
        if self.id is not None:
            result['id'] = self.id
        return result

    def get_id(self):
        """
        Returns the task id.

        @rtype:  str
        @return: The id of the task.
        """
        return self.id

    def set_job_id(self, job_id):
        """
        Associate the task with the Exscript.workqueue.Job with the given
        id.

        @type  job_id: int
        @param job_id: The id of the job.
        """
        self.touch()
        self.job_id = job_id
        self.set_status('queued')

    def get_job_id(self):
        """
        Returns the associated Exscript.workqueue.Job, or None.

        @type  job_id: str
        @param job_id: The id of the task.
        """
        return self.job_id

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
        self.changed_event(self)

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
        Returns the progress as a string, in percent.

        @rtype:  str
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

    def set_logfile(self, *logfile):
        """
        Set the name of the logfile, and set the name of the tracefile
        to the same name with '.error' appended.

        @type  logfile: string
        @param logfile: A filename.
        """
        self.touch()
        self.logfile   = os.path.join(*logfile)
        self.tracefile = self.logfile + '.error'

    def get_logfile(self):
        """
        Returns the name of the logfile as a string.

        @rtype:  string|None
        @return: A filename, or None.
        """
        return self.logfile

    def set_tracefile(self, tracefile):
        """
        Set the name of the tracefile.

        @type  tracefile: string
        @param tracefile: A filename.
        """
        self.touch()
        self.tracefile = os.path.join(*tracefile)

    def get_tracefile(self):
        """
        Returns the name of the tracefile as a string.

        @rtype:  string|None
        @return: A filename, or None.
        """
        return self.tracefile

    def set(self, key, value):
        """
        Defines a variable that is carried along with the task.
        The value *must* be pickleable.
        """
        self.vars[key] = value

    def get(self, key, default = None):
        """
        Returns the value as previously defined by L{Task.set()}.
        """
        return self.vars.get(key, default)
