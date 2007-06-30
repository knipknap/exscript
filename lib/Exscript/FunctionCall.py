import Expression
from Token      import Token
from Variable   import Variable

class FunctionCall(Token):
    def __init__(self, parser, parent):
        Token.__init__(self, 'FunctionCall', parser)
        self.parent    = parent
        self.funcname  = None
        self.arguments = []

        # Extract the function name.
        (type, token) = parser.token()
        parser.expect('open_function_call')
        self.funcname = token[:-1]
        function      = self.parent.get(self.funcname)
        if function is None:
            parent.syntax_error(self, 'Undefined function %s' % self.funcname)

        # Parse the argument list.
        (type, token) = parser.token()
        while 1:
            if parser.next_if('close_bracket'):
                break
            self.arguments.append(Expression.Expression(parser, parent))
            (type, token) = parser.token()
            if not parser.next_if('comma') and not parser.current_is('close_bracket'):
                error = 'Expected separator or argument list end but got %s' % type
                parent.syntax_error(self, error)


    def dump(self, indent = 0):
        print (' ' * indent) + self.name, self.funcname, 'start'
        for argument in self.arguments:
            argument.dump(indent + 1)
        print (' ' * indent) + self.name, self.funcname, 'end'


    def value(self):
        argument_values = [arg.value() for arg in self.arguments]
        function        = self.parent.get(self.funcname)
        if function is None:
            self.parent.runtime_error(self, 'Undefined function %s' % self.funcname)
        return function(self.parent, *argument_values)
