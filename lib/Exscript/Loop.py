import Exscript
from Token import Token
from Term  import Term

class Loop(Token):
    def __init__(self, parser, scope):
        Token.__init__(self, 'Loop', parser)

        # Expect a variable name.
        parser.expect('whitespace')
        (type, self.list_varname) = parser.token()
        self.list_variable = Term(parser, scope)

        # Expect the "as" keyword.
        parser.next_if('whitespace')
        parser.expect('keyword', 'as')

        # The iterator variable.
        parser.next_if('whitespace')
        (type, self.iter_variable) = parser.token()
        parser.expect('varname')
        scope.define(**{self.iter_variable: []})

        # End of statement.
        parser.next_if('whitespace')
        if not parser.next_if('close_curly_bracket'):
            token = parser.token()
            error = 'Unexpected %s at end of loop: %s' % token
            parser.syntax_error(error)

        # Body of the loop block.
        while parser.next_if('newline') or parser.next_if('whitespace'):
            pass
        self.block = Exscript.Exscript(parser, scope)


    def value(self):
        for value in self.list_variable.value():
            self.block.define(**{self.iter_variable: value})
            self.block.value()
        return 1


    def dump(self, indent = 0):
        print (' ' * indent) + self.name,
        print self.list_varname, 'as', self.iter_variable, 'start'
        self.block.dump(indent + 1)
        print (' ' * indent) + self.name, 'end'
