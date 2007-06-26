from Token import Token

class Variable(Token):
    def __init__(self, parent, varname):
        Token.__init__(self, 'Variable', parent.parser)
        self.parent  = parent
        self.varname = varname


    def value(self):
        val = self.parent.get(self.varname)
        if val is None:
             self.parser.runtime_error(self, 'Undefined variable %s' % name)
        return val


    def dump(self, indent = 0):
        print (' ' * indent) + 'Variable', self.varname
