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

def _underline(text, line = '-'):
    return [text, line * len(text)]

def _get_action_name(action, retry = 0):
    if retry == 0:
        return action.get_name()
    return action.get_name() + ' (retry %d)' % retry

def _get_successful_logs_from_action(logger, action):
    return [l for l in logger.get_logs(action) if not l.has_aborted()]

def _get_failed_logs_from_action(logger, action):
    return [l for l in logger.get_logs(action) if l.has_aborted()]

def summarize(logger):
    """
    Creates a short summary on the actions that were logged by the given
    Logger.

    @type  logger: Logger
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

def format(logger,
           show_successful = True,
           show_errors     = True,
           show_traceback  = True):
    """
    Prints a report of the actions that were logged by the given Logger.
    The report contains a list of successful actions, as well as the full
    error message on failed actions.

    @type  logger: Logger
    @param logger: The logger that recorded what happened in the queue.
    @rtype:  string
    @return: A string summarizing the status of every performed task.
    """
    output = []

    # Print failed actions.
    errors = logger.get_failed_actions()
    if show_errors and errors:
        output += _underline('Failed actions:')
        for action in errors:
            for n, log in enumerate(logger.get_logs(action)):
                name = _get_action_name(action, n)
                if show_traceback:
                    output.append(name + ':')
                    output.append(log.get_error())
                else:
                    output.append(name + ': ' + log.get_error(False))
        output.append('')

    # Print successful actions.
    if show_successful:
        output += _underline('Successful actions:')
        for action in logger.get_successful_actions():
            n_errors = len(_get_failed_logs_from_action(logger, action))
            if n_errors == 0:
                status = ''
            elif n_errors == 1:
                status = ' (required one retry)'
            else:
                status = ' (required %d retries)' % n_errors
            output.append(_get_action_name(action) + status)
        output.append('')

    return '\n'.join(output).strip()
