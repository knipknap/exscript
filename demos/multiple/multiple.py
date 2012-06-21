#!/usr/bin/env python
from Exscript            import Host
from Exscript.util.file  import get_hosts_from_file, get_accounts_from_file
from Exscript.util.start import start

def one(job, host, conn):
    # You can add a safehold based on the guess_os() method.
    if conn.guess_os() != 'ios':
        raise Exception('unsupported os: ' + repr(conn.guess_os()))

    # autoinit() automatically executes commands to make the remote
    # system behave more script-friendly. The specific commands depend
    # on the detected operating system, i.e. on what guess_os() returns.
    conn.autoinit()

    # Execute a simple command.
    conn.execute('show ip int brie')
    print "myvariable is", conn.get_host().get('myvariable')

def two(job, host, conn):
    conn.autoinit()
    conn.execute('show interface POS1/0')

accounts = get_accounts_from_file('accounts.cfg')

# Start on one host.
host = Host('localhost')
host.set('myvariable', 'foobar')
start(accounts, host1, one)

# Start on many hosts. In this case, the accounts from accounts.cfg
# are only used if the host url does not contain a username and password.
# The "max_threads" keyword indicates the maximum number of concurrent
# connections.
hosts = get_hosts_from_file('hostlist.txt')
start(accounts, hosts, two, max_threads = 2)
