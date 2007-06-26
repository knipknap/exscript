from Token     import Token
from Trackable import Trackable

class Scope(Token, Trackable):
    def __init__(self, name, parser, parent, *args, **kwargs):
        Trackable.__init__(self)
        Token.__init__(self, name, parser)
        self.variables      = kwargs.get('variables', {})
        self.children       = []
        self.parent         = parent
        self.exit_requested = 0


    def exit_request(self):
        self.exit_requested = 1


    def define(self, *args, **kwargs):
        if self.parent is None:
            self.variables.update(kwargs)
        else:
            self.parent.define(**kwargs)


    def is_defined(self, name):
        if self.variables.has_key(name):
            return 1
        if self.parent is not None:
            return self.parent.is_defined(name)
        return 0


    def get(self, name):
        if self.variables.has_key(name):
            return self.variables[name]
        if self.parent is None:
            return None
        return self.parent.get(name)


    def value(self):
        result = 1
        for child in self.children:
            result = child.value()
        return result


    def dump(self, indent = 0):
        print (' ' * indent) + self.name, 'start'
        for child in self.children:
            child.dump(indent + 1)
        print (' ' * indent) + self.name, 'end'
