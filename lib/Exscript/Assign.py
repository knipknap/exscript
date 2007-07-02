import Expression
from Token import Token

class Assign(Token):
    def __init__(self, parser, parent):
        Token.__init__(self, 'Assign', parser)
        self.parent = parent

        # Extract the variable name.
        (type, self.varname) = parser.token()
        parser.expect('varname')
        parser.expect('whitespace')
        parser.expect('assign')
        parser.expect('whitespace')
        self.expression = Expression.Expression(parser, parent)
        self.parent.define(**{self.varname: None})


    def dump(self, indent = 0):
        print (' ' * indent) + self.name, self.varname, 'start'
        self.expression.dump(indent + 1)
        print (' ' * indent) + self.name, self.varname, 'start'


    def value(self):
        result = self.expression.value()
        self.parent.define(**{self.varname: result})
        return result
