#!/usr/bin/env python3
from Exscript.util.match import any_match
from Exscript.util.start import quickstart


def do_something(job, host, conn):
    conn.execute('ls -1')
    files = any_match(conn, r'(\S+)')
    print("Files found:", files)


# Open a connection (SSH2, by default) to each of the hosts, and run do_something(). To
# open the connection via Telnet or SSH Netconf, you may prefix the hostname by the
# protocol, e.g.: 'telnet://hostname', 'netconf://hostname', etc.
quickstart(('localhost', 'otherhost'), do_something)
