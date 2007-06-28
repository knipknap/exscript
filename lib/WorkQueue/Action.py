import os
from Trackable      import Trackable
from AbstractMethod import AbstractMethod

True  = 1
False = 0

class Action(Trackable):
    def __init__(self, *args, **kwargs):
        Trackable.__init__(self)
        self.debug = kwargs.get('debug', 0)


    def execute(self, global_context, local_context):
        AbstractMethod(self)
