#!/usr/bin/env python3
from Exscript.util.start import quickstart
from Exscript.util.template import eval_file


def do_something(job, host, conn):
    assert conn.guess_os() == 'shell'
    conn.execute('ls -1')
    eval_file(conn, 'template.exscript', foobar='hello-world')


quickstart('ssh://localhost', do_something)
