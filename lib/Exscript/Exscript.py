import re
from Scope   import Scope
from Code    import Code
from Execute import Execute

grammar = (
    ('escaped_data',        r'\\{'),
    ('open_curly_bracket',  '{'),
    ('newline',             r'\n'),
    ('raw_data',            r'[^\r\n{}]+')
)

grammar_c = []
for type, regex in grammar:
    grammar_c.append((type, re.compile(regex)))

class Exscript(Scope):
    def __init__(self, parser, parent, *args, **kwargs):
        Scope.__init__(self, 'Exscript', parser, parent, **kwargs)
        parser.set_grammar(grammar_c)
        #print "Opening Scope:", parser.token()
        buffer = ''
        while 1:
            if self.exit_requested or parser.current_is('EOF'):
                break
            elif parser.next_if('open_curly_bracket'):
                if buffer.strip() != '':
                    self.children.append(Execute(parser, self, buffer))
                    buffer = ''
                code = Code(parser, self)
                self.children.append(code)
            elif parser.current_is('raw_data'):
                buffer += parser.token()[1]
                parser.next()
            elif parser.current_is('escaped_data'):
                buffer += parser.token()[1][1]
                parser.next()
            elif parser.next_if('newline'):
                if buffer.strip() != '':
                    self.children.append(Execute(parser, self, buffer))
                    buffer = ''
            else:
                type = parser.token()[0]
                parser.syntax_error('Unexpected %s' % type)
        parser.restore_grammar()


    def execute(self):
        return self.value()
