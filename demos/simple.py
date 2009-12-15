#!/usr/bin/env python
from Exscript.util.file     import get_hosts_from_file
from Exscript.util.match    import any_match
from Exscript.util.template import eval_file
from Exscript.util.start    import quickstart

def do_something(conn):
    conn.execute('show ip int brie')
    ge_interfaces = any_match(conn, r'(Gigabit\S+)')
    eval_file(conn, 'mytemplate.exscript', interfaces = ge_interfaces)

# Read a list of hostnames from a file.
hosts = get_hosts_from_file('hostlist.txt')

# Open a connection (Telnet, by default) to each of the hosts, and run
# do_something(). To open the connection via SSH, you may prefix the
# hostname by the protocol, e.g.: 'ssh://hostname', 'telnet://hostname',
# etc.
# The "max_threads" keyword indicates the maximum number of concurrent
# connections.
quickstart(hosts, do_something, max_threads = 5)
