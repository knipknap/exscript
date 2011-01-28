#!/usr/bin/env python
from Exscript.util.match    import any_match
from Exscript.util.template import eval_file
from Exscript.util.start    import quickstart

def do_something(conn):
    conn.execute('ls -1')
    files = any_match(conn, r'(\S+)')
    print "Files found:", files

# Open a connection (Telnet, by default) to each of the hosts, and run
# do_something(). To open the connection via SSH, you may prefix the
# hostname by the protocol, e.g.: 'ssh://hostname', 'telnet://hostname',
# etc.
quickstart(('localhost', 'otherhost'), do_something)
