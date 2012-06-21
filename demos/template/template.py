#!/usr/bin/env python
from Exscript.util.template import eval_file
from Exscript.util.start    import quickstart

def do_something(job, host, conn):
    assert conn.guess_os() == 'shell'
    conn.execute('ls -1')
    eval_file(conn, 'template.exscript', foobar = 'hello-world')

quickstart('ssh://xpc3', do_something)
