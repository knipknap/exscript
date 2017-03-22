#
# Copyright (C) 2010-2017 Samuel Abels
# The MIT License (MIT)
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Formatting logs into human readable reports.
"""


def _underline(text, line='-'):
    return [text, line * len(text)]


def status(logger):
    """
    Creates a one-line summary on the actions that were logged by the given
    Logger.

    :type  logger: Logger
    :param logger: The logger that recorded what happened in the queue.
    :rtype:  string
    :return: A string summarizing the status.
    """
    aborted = logger.get_aborted_actions()
    succeeded = logger.get_succeeded_actions()
    total = aborted + succeeded
    if total == 0:
        return 'No actions done'
    elif total == 1 and succeeded == 1:
        return 'One action done (succeeded)'
    elif total == 1 and succeeded == 0:
        return 'One action done (failed)'
    elif total == succeeded:
        return '%d actions total (all succeeded)' % total
    elif succeeded == 0:
        return '%d actions total (all failed)' % total
    else:
        msg = '%d actions total (%d failed, %d succeeded)'
        return msg % (total, aborted, succeeded)


def summarize(logger):
    """
    Creates a short summary on the actions that were logged by the given
    Logger.

    :type  logger: Logger
    :param logger: The logger that recorded what happened in the queue.
    :rtype:  string
    :return: A string summarizing the status of every performed task.
    """
    summary = []
    for log in logger.get_logs():
        thestatus = log.has_error() and log.get_error(False) or 'ok'
        name = log.get_name()
        summary.append(name + ': ' + thestatus)
    return '\n'.join(summary)


def format(logger,
           show_successful=True,
           show_errors=True,
           show_traceback=True):
    """
    Prints a report of the actions that were logged by the given Logger.
    The report contains a list of successful actions, as well as the full
    error message on failed actions.

    :type  logger: Logger
    :param logger: The logger that recorded what happened in the queue.
    :rtype:  string
    :return: A string summarizing the status of every performed task.
    """
    output = []

    # Print failed actions.
    errors = logger.get_aborted_actions()
    if show_errors and errors:
        output += _underline('Failed actions:')
        for log in logger.get_aborted_logs():
            if show_traceback:
                output.append(log.get_name() + ':')
                output.append(log.get_error())
            else:
                output.append(log.get_name() + ': ' + log.get_error(False))
        output.append('')

    # Print successful actions.
    if show_successful:
        output += _underline('Successful actions:')
        for log in logger.get_succeeded_logs():
            output.append(log.get_name())
        output.append('')

    return '\n'.join(output).strip()
