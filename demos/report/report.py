#!/usr/bin/env python
from Exscript                import Queue, Logger
from Exscript.util.decorator import autologin
from Exscript.util.file      import get_hosts_from_file, get_accounts_from_file
from Exscript.util.report    import status, summarize

@autologin
def do_something(conn):
    conn.execute('show ip int brie')

# Read input data.
accounts = get_accounts_from_file('accounts.cfg')
hosts    = get_hosts_from_file('hostlist.txt')

# Run do_something on each of the hosts. The given accounts are used
# round-robin. "verbose = 0" instructs the queue to not generate any
# output on stdout. Using "logdir = ..." is equivalent to the following:
#   logger = FileLogger(queue, 'my/logdir')
# It instructs the queue to automatically log everything to the filesystem;
# one file is created per host.
queue  = Queue(verbose = 0, max_threads = 5, logdir = 'my/logdir/')
logger = Logger(queue)          # Logs everything to memory.
queue.add_account(accounts)     # Adds one or more accounts.
queue.run(hosts, do_something)  # Asynchronously enqueues all hosts.
queue.shutdown()                # Waits until all hosts are completed.

# Print a short report.
print status(logger)
print summarize(logger)
