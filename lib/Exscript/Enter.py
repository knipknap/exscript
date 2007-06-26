from Token   import Token
from Execute import Execute

class Enter(Token):
    def __init__(self, parser, parent):
        Token.__init__(self, 'Enter', parser)
        self.parent  = parent

        parser.expect('keyword', 'enter')
        while parser.next_if('whitespace') or parser.next_if('newline'):
            pass

        self.execute = Execute(parser, parent, '')


    def value(self):
        return self.execute.value()


    def dump(self, indent = 0):
        print (' ' * indent) + self.name
        self.execute.dump(indent + 1)
