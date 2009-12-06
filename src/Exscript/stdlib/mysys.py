# Copyright (C) 2007 Samuel Abels, http://debain.org
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
import time

True  = 1
False = 0

def message(scope, string):
    """
    Writes the given string to stdout.

    @type  string: string
    @param string: A string, or a list of strings.
    """
    exscript = scope.get('__connection__').get_queue()
    exscript._print(string[0] + '\n')
    return True

def tacacs_lock(scope, user):
    """
    Acquire an exclusive lock on the account of the user with the given
    name.

    @type  user: string
    @param user: A username.
    """
    accm    = scope.get('__connection__').get_account_manager()
    account = accm.get_account_from_name(user[0])
    accm.acquire_account(account)
    return True

def tacacs_unlock(scope, user):
    """
    Release the exclusive lock on the account of the user with the given
    name.

    @type  user: string
    @param user: A username.
    """
    accm    = scope.get('__connection__').get_account_manager()
    account = accm.get_account_from_name(user[0])
    account.release()
    return True

def run(scope, hostnames, filename):
    """
    Runs the template file with the given name on the host with the given
    hostname. If the filename is not absolute, it is relative to the path
    of the script that makes the call.
    Any variables that are defined in the current scope of the calling
    script are also passed to the template.

    @type  hostnames: string
    @param hostnames: A hostname, or a list of hostnames.
    @type  filename: string
    @param filename: The name of the Exscript file to be executed.
    """
    # The filename is relative to the file that makes the call.
    exscript_file = scope.get('__filename__') or ''
    exscript_dir  = os.path.dirname(exscript_file)
    filename      = os.path.join(exscript_dir, filename[0])

    # Copy the variables from the current scope into new host objects.
    vars  = scope.get_public_vars()
    hosts = []
    for hostname in hostnames:
        host = Host(hostname)
        for key, value_list in vars.iteritems():
             for value in value_list:
                 host.append(key, value)
        hosts.append(host)

    # Enqueue the new jobs.
    strip    = scope.parser.strip_command
    job      = bind_args(eval_file, filename, strip_command)
    exscript = scope.get('__connection__').get_queue()
    actions  = exscript._priority_run(hosts, autologin(job))

    # Wait until all jobs are completed.
    while not exscript._action_is_completed(actions):
        time.sleep(1)
        continue
    return True

def wait(scope, seconds):
    """
    Waits for the given number of seconds.

    @type  seconds: int
    @param seconds: The wait time in seconds.
    """
    time.sleep(int(seconds[0]))
    return True
