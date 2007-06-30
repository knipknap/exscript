import Exscript
from Scope     import Scope
from Exception import DeviceException

class Try(Scope):
    def __init__(self, parser, parent):
        Scope.__init__(self, 'Try', parser, parent)

        # End of expression.
        parser.next_if('whitespace')
        parser.expect('keyword', 'try')
        if not parser.next_if('close_curly_bracket'):
            token = parser.token()
            error = 'Unexpected %s at end of "try" keyword: %s' % token
            parent.syntax_error(self, error)

        # Body of the ignore_errors block.
        while parser.next_if('newline') or parser.next_if('whitespace'):
            pass
        self.block = Exscript.Exscript(parser, parent)


    def value(self):
        try:
            self.block.value()
        except DeviceException, e:
            return 1
        return 1


    def dump(self, indent = 0):
        print (' ' * indent) + self.name, 'start'
        self.block.dump(indent + 1)
        print (' ' * indent) + self.name, 'end'
