from Token import Token

class Variable(Token):
    def __init__(self, parser, parent):
        Token.__init__(self, 'Variable', parser)
        self.parent  = parent

        (type, self.varname) = parser.token()
        parser.expect('varname')


    def value(self):
        val = self.parent.get(self.varname)
        if val is None:
             self.parent.runtime_error(self, 'Undefined variable %s' % name)
        return val


    def dump(self, indent = 0):
        print (' ' * indent) + 'Variable', self.varname
