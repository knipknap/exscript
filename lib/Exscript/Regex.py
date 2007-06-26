import re
from Token import Token

grammar = (
    ('escaped_data',    r'\\/'),
    ('regex_data',      r'[^/\r\n\/]+'),
    ('regex_delimiter', r'/'),
)

grammar_c = []
for type, regex in grammar:
    grammar_c.append((type, re.compile(regex)))

class Regex(Token):
    def __init__(self, parser):
        Token.__init__(self, 'Regular Expression', parser)
        parser.set_grammar(grammar_c)
        regex = ''
        while 1:
            if parser.current_is('regex_data'):
                regex += parser.token()[1]
                parser.next()
            elif parser.current_is('escaped_data'):
                regex += parser.token()[1][1]
                parser.next()
            elif parser.next_if('regex_delimiter'):
                break
            else:
                type = parser.token()[0]
                parser.syntax_error('Expected regular expression but got %s' % type)
        self.regex = re.compile(regex)
        parser.restore_grammar()


    def value(self):
        return self.regex


    def dump(self, indent = 0):
        print (' ' * indent) + self.name, self.regex.pattern
