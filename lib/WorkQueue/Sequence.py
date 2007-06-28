import threading
from Action import Action

True  = 1
False = 0

class Sequence(Action):
    def __init__(self, *args, **kwargs):
        Action.__init__(self)
        self.actions = []
        if kwargs.has_key('actions'):
            assert type(kwargs['actions']) == type([])
            for action in kwargs['actions']:
                self.add(action)


    def add(self, action):
        self.actions.append(action)


    def execute(self, global_context, local_context):
        assert local_context  is not None
        assert global_context is not None
        for action in self.actions:
            action.debug = self.debug
            if not action.execute(global_context, local_context):
                return False
        return True
