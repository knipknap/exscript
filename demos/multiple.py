#!/usr/bin/env python
from Exscript               import Host
from Exscript.util.interact import read_login
from Exscript.util.template import eval_file
from Exscript.util.start    import start

def one(conn):
    conn.open()
    conn.authenticate()
    conn.autoinit()
    conn.execute('show ip int brie')

def two(conn):
    eval_file(conn, 'mytemplate.exscript', interface = 'POS1/0')

account = read_login()

# Start on one host.
host1 = Host('localhost')
host1.set('myvariable', 'foobar')
start(account, host1, one)

# Start on another.
host2 = Host('otherhost1')
host3 = Host('otherhost2')
start(account, [host1, host2], two)
