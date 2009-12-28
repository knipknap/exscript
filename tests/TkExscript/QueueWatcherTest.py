import time, Exscript.util.sigintcatcher
from Exscript                import Queue, Account
from Exscript.util.decorator import bind
from Tkinter                 import *
from TkExscript              import QueueWatcher

def do_something(conn, wait):
    conn.open()
    conn.authenticate()
    for i in range(100):
        conn.execute('test%d' % i)
        time.sleep(wait)
    conn.close()

class Window(Frame):
    def __init__(self):
        self.widget = None
        Frame.__init__(self)
        self.pack(expand = True, fill = BOTH)

        self.queue = Queue(max_threads = 4, verbose = 0)
        self.queue.add_account(Account('test', 'test'))

        self.widget = QueueWatcher(self, self.queue)
        self.widget.pack(expand = True, fill = BOTH, padx = 6, pady = 6)

        self.queue.run('dummy:dummy1', bind(do_something, .02))
        self.queue.run('dummy:dummy2', bind(do_something, .2))
        self.queue.run('dummy:dummy3', bind(do_something, .3))

app = Window()
app.mainloop()
app.queue.shutdown()
