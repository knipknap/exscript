import time, Exscript.util.sigintcatcher
from Exscript                import Queue, Account
from Exscript.util.decorator import bind
from TkExscript              import QueueWindow

def do_something(conn, wait):
    conn.open()
    conn.authenticate()
    for i in range(100):
        conn.execute('test%d' % i)
        time.sleep(wait)
    conn.close()

queue = Queue(max_threads = 4, verbose = 0)
queue.add_account(Account('test', 'test'))
window = QueueWindow(queue)
queue.run('dummy:dummy1', bind(do_something, .02))
queue.run('dummy:dummy2', bind(do_something, .2))
queue.run('dummy:dummy3', bind(do_something, .3))
window.mainloop()
queue.shutdown()
