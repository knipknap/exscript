import re
from Scope        import Scope
from Assign       import Assign
from Enter        import Enter
from Extract      import Extract
from FunctionCall import FunctionCall
from IfCondition  import IfCondition
from Loop         import Loop
from Try          import Try

varname_re = r'[a-zA-Z][\w_]+'

grammar = (
    ('escaped_data',        r'\\.'),
    ('regex_delimiter',     r'/'),
    ('string_delimiter',    r'"'),
    ('open_curly_bracket',  r'{'),
    ('close_curly_bracket', r'}'),
    ('close_bracket',       r'\)'),
    ('comma',               r','),
    ('whitespace',          r'[ \t]+'),
    ('keyword',             r'\b(?:extract|as|if|else|end|loop|try|enter)\b'),
    ('assign',              r'='),
    ('comparison',          r'\b(?:is\s+not|is|ge|gt|le|lt|matches)\b'),
    ('arithmetic_operator', r'(?:\*|\+|-|/)'),
    ('logical_operator',    r'\b(?:and|or|not)\b'),
    ('open_function_call',  varname_re + r'(?:\.' + varname_re + r')*\('),
    ('varname',             varname_re),
    ('number',              r'\d+'),
    ('newline',             r'\n'),
    ('raw_data',            r'[^\r\n{}]+')
)

grammar_c = []
for type, regex in grammar:
    grammar_c.append((type, re.compile(regex)))

class Code(Scope):
    def __init__(self, parser, parent):
        Scope.__init__(self, 'Code', parser, parent)
        parser.set_grammar(grammar_c)
        while 1:
            if parser.next_if('close_curly_bracket'):
                break
            elif parser.next_if('whitespace') or parser.next_if('newline'):
                pass
            elif parser.next_if('keyword', 'extract'):
                self.children.append(Extract(parser, self))
            elif parser.next_if('keyword', 'if'):
                self.children.append(IfCondition(parser, self))
            elif parser.next_if('keyword', 'loop'):
                self.children.append(Loop(parser, self))
            elif parser.current_is('varname'):
                self.children.append(Assign(parser, self))
            elif parser.current_is('keyword', 'try'):
                self.children.append(Try(parser, self))
            elif parser.current_is('keyword', 'enter'):
                self.children.append(Enter(parser, self))
            elif parser.current_is('keyword', 'else'):
                parent.exit_request()
                break
            elif parser.next_if('keyword', 'end'):
                parent.exit_request()
                while parser.next_if('whitespace') or parser.next_if('newline'):
                    pass
                break
            elif parser.current_is('open_function_call'):
                self.children.append(FunctionCall(parser, self))
            else:
                (type, token) = parser.token()
                parent.syntax_error(self, 'Unexpected %s "%s"' % (type, token))
        parser.restore_grammar()
