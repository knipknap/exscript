import Exscript
from Token      import Token
from Expression import Expression

class IfCondition(Token):
    def __init__(self, parser, scope):
        Token.__init__(self, 'If-condition', parser)

        # Expect an expression.
        parser.expect('whitespace')
        self.expression = Expression(parser, scope)

        # End of expression.
        parser.next_if('whitespace')
        if not parser.next_if('close_curly_bracket'):
            token = parser.token()
            error = 'Unexpected %s at end of if-condition: %s' % token
            parser.syntax_error(error)

        # Body of the if block.
        while parser.next_if('newline') or parser.next_if('whitespace'):
            pass
        self.block = Exscript.Exscript(parser, scope)


    def value(self):
        if self.expression.value():
            self.block.value()
        return 1


    def dump(self, indent = 0):
        print (' ' * indent) + self.name, 'start'
        self.expression.dump(indent + 1)
        self.block.dump(indent + 1)
        print (' ' * indent) + self.name, 'end'
