import Exscript
from Token      import Token
from Term       import Term
from Expression import Expression

class Loop(Token):
    def __init__(self, parser, scope):
        Token.__init__(self, 'Loop', parser)
        self.during         = None
        self.until          = None
        self.list_variables = []
        self.iter_varnames  = []

        # Expect one ore more lists.
        parser.expect('whitespace')
        if not parser.current_is('keyword', 'while') and \
           not parser.current_is('keyword', 'until'):
            self.list_variables = [Term(parser, scope)]
            parser.next_if('whitespace')
            while parser.next_if('comma'):
                parser.next_if('whitespace')
                self.list_variables.append(Term(parser, scope))
                parser.next_if('whitespace')

            # Expect the "as" keyword.
            parser.expect('keyword', 'as')

            # The iterator variable.
            parser.next_if('whitespace')
            (type, iter_varname) = parser.token()
            parser.expect('varname')
            scope.define(**{iter_varname: []})
            self.iter_varnames = [iter_varname]
            parser.next_if('whitespace')
            while parser.next_if('comma'):
                parser.next_if('whitespace')
                (type, iter_varname) = parser.token()
                parser.expect('varname')
                scope.define(**{iter_varname: []})
                self.iter_varnames.append(iter_varname)
                parser.next_if('whitespace')

        # Check if this is a "while" loop.
        if parser.next_if('keyword', 'while'):
            parser.expect('whitespace')
            self.during = Expression(parser, scope)
            parser.next_if('whitespace')
        
        # Check if this is an "until" loop.
        if parser.next_if('keyword', 'until'):
            parser.expect('whitespace')
            self.until = Expression(parser, scope)
            parser.next_if('whitespace')
        
        # End of statement.
        parser.next_if('whitespace')
        if not parser.next_if('close_curly_bracket'):
            token = parser.token()
            error = 'Unexpected %s at end of loop: %s' % token
            parent.syntax_error(self, error)

        if len(self.iter_varnames) != len(self.list_variables):
            error = '%s lists, but only %s iterators in loop' % (len(self.iter_varnames),
                                                                 len(self.list_variables))
            parent.syntax_error(self, error)

        # Body of the loop block.
        while parser.next_if('newline') or parser.next_if('whitespace'):
            pass
        self.block = Exscript.Exscript(parser, scope)


    def value(self):
        if len(self.list_variables) == 0:
            # If this is a "while" loop, iterate as long as the condition is True.
            if self.during is not None:
                while self.during.value():
                    self.block.value()
                return 1

            # If this is an "until" loop, iterate until the condition is True.
            if self.until is not None:
                while not self.until.value():
                    self.block.value()
                return 1

        # Retrieve the lists from the list terms.
        lists = [var.value() for var in self.list_variables]
        
        # Make sure that all lists have the same length.
        for list in lists:
            if len(list) != len(lists[0]):
                msg = 'All list variables must have the same length'
                self.runtime_error(self, msg)

        # Iterate.
        for i in xrange(len(lists[0])):
            for f, list in enumerate(lists):
                self.block.define(**{self.iter_varnames[f]: [list[i]]})
            if self.until is not None and self.until.value():
                break
            if self.during is not None and not self.during.value():
                break
            self.block.value()
        return 1


    def dump(self, indent = 0):
        print (' ' * indent) + self.name,
        print self.list_variables, 'as', self.iter_varnames, 'start'
        self.block.dump(indent + 1)
        print (' ' * indent) + self.name, 'end'
