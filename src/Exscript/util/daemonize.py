# Copyright (C) 2007-2011 Samuel Abels.
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
Daemonizing a process.
"""
import sys
import os

def _redirect_output(filename):
    out_log  = open(filename, 'a+', 0)
    err_log  = open(filename, 'a+', 0)
    dev_null = open(os.devnull, 'r')
    os.close(sys.stdin.fileno())
    os.close(sys.stdout.fileno())
    os.close(sys.stderr.fileno())
    os.dup2(out_log.fileno(), sys.stdout.fileno())
    os.dup2(err_log.fileno(), sys.stderr.fileno())
    os.dup2(dev_null.fileno(), sys.stdin.fileno())

def _fork_exit(): # UNIX only
    pid = os.fork()
    if pid > 0:
        sys.exit(0)

def daemonize():
    """
    Forks and daemonizes the current process. Does not automatically track
    the process id; to do this, use L{Exscript.util.pidutil}.
    """
    sys.stdout.flush()
    sys.stderr.flush()

    if sys.platform == 'win32': # borrowed from http.server module
        import subprocess
        interp = sys.executable
        if interp.lower().endswith("w.exe"): # On Windows, use python.exe
            interp = interp[:-5] + interp[-4:]
        cmdline = [interp, '-u'] + sys.argv[1:] # ToDo: handle this flag to use files for logging and error reporting.
        p = subprocess.Popen(cmdline,
                             stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL,
                             creationflags=subprocess.CREATE_NEW_CONSOLE,
                             close_fds=True, shell=False, env=env)
        sys.exit(0)
    else: # UNIX double-fork magic. We need to fork before any threads are created.
        _fork_exit() # Exit first parent.
        os.chdir('/')
        os.setsid()  # Decouple from parent environment.
        os.umask(0)
        _fork_exit() # Now fork again to exit second parent.
        _redirect_output(os.devnull)

