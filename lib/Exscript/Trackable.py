class Slot:
    def __init__(self):
        self.subscribers = []

    def subscribe(self, func):
        self.subscribers.append(func)

    def emit(self, name, *args, **kwargs):
        for func in self.subscribers:
            func(name, **kwargs)


class Trackable:
    def __init__(self):
        self.slots = {}

    def signal_connect(self, name, func):
        if not self.slots.has_key(name):
            self.slots[name] = Slot()
        self.slots[name].subscribe(func)

    def emit(self, name, *args, **kwargs):
        if not self.slots.has_key(name):
            return
        self.slots[name].emit(name, **kwargs)
