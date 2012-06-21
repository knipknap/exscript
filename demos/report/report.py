#!/usr/bin/env python
from Exscript                import Queue, Logger
from Exscript.util.log       import log_to
from Exscript.util.decorator import autologin
from Exscript.util.file      import get_hosts_from_file, get_accounts_from_file
from Exscript.util.report    import status, summarize

logger = Logger() # Logs everything to memory.

@log_to(logger)
@autologin
def do_something(job, host, conn):
    conn.execute('show ip int brie')

# Read input data.
accounts = get_accounts_from_file('accounts.cfg')
hosts    = get_hosts_from_file('hostlist.txt')

# Run do_something on each of the hosts. The given accounts are used
# round-robin. "verbose = 0" instructs the queue to not generate any
# output on stdout.
queue = Queue(verbose = 0, max_threads = 5)
queue.add_account(accounts)     # Adds one or more accounts.
queue.run(hosts, do_something)  # Asynchronously enqueues all hosts.
queue.shutdown()                # Waits until all hosts are completed.

# Print a short report.
print status(logger)
print summarize(logger)
