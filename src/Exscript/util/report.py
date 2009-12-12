# Copyright (C) 2007-2009 Samuel Abels.
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

def summarize(logger):
    """
    Creates a short summary on the actions that were logged by the given
    QueueLogger.

    @type  logger: QueueLogger
    @param logger: The logger that recorded what happened in the queue.
    @rtype:  string
    @return: A string summarizing the status of every performed task.
    """
    summary = []
    for action in logger.get_logged_actions():
        for n, log in enumerate(logger.get_logs(action)):
            status = log.has_aborted() and log.get_error(False) or 'ok'
            name   = log.get_host().get_address()
            if n > 0:
                name += ' (retry %d)' % n
            summary.append(name + ': ' + status)
    return '\n'.join(summary)
