import os, sys
from pyinotify import WatchManager, Notifier, ProcessEvent, EventsCodes

def monitor(path, callback):
    # Create the event handler.
    class PClose(ProcessEvent):
        def process_IN_CLOSE(self, event):
            # Not a new file? Return.
            if not event.name:
                return

            # Invoke the callback.
            filename = os.path.join(event.path, event.name)
            callback(filename)

    # Init inotify.
    manager  = WatchManager()
    notifier = Notifier(manager, PClose())
    manager.add_watch(path, EventsCodes.IN_CLOSE_WRITE)

    # Loop forever.
    try:
        while True:
            notifier.process_events()
            if notifier.check_events():
                notifier.read_events()
    finally:
        notifier.stop()

if __name__ == '__main__':
    def cb(path):
        print "CLOSE:", path
    try:
        path = sys.argv[1]
    except IndexError:
        print 'use: %s dir' % sys.argv[0]
    else:
        monitor(path, cb)
