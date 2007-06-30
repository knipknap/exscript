from Token        import Token
from Variable     import Variable
from Number       import Number
from FunctionCall import FunctionCall
from String       import String
from Regex        import Regex

class Term(Token):
    def __init__(self, parser, parent):
        Token.__init__(self, 'Term', parser)
        self.term = None
        self.lft  = None
        self.rgt  = None
        self.op   = None

        # Expect a term.
        (type, token) = parser.token()
        if parser.current_is('varname'):
            if not parent.is_defined(token):
                parent.generic_error(self, 'Error', 'Undeclared variable %s' % token)
            self.term = Variable(parser, parent)
        elif parser.current_is('open_function_call'):
            self.term = FunctionCall(parser, parent)
        elif parser.next_if('string_delimiter'):
            self.term = String(parser, parent)
        elif parser.next_if('number'):
            self.term = Number(token)
        elif parser.next_if('regex_delimiter'):
            self.term = Regex(parser)
        else:
            parent.syntax_error(self, 'Expected term but got %s' % type)


    def priority(self):
        return 6


    def value(self):
        return self.term.value()


    def dump(self, indent = 0):
        print (' ' * indent) + self.name
        self.term.dump(indent + 1)
