from Exscript import Exscript
from Scope    import Scope

class Program(Scope):
    def __init__(self, parser, *args, **kwargs):
        Scope.__init__(self, 'Program', parser, None, **kwargs)
        self.input = parser.input
        self.children.append(Exscript(parser, self))


    def get_line_position_from_char(self, char):
        line_start = char
        while line_start != 0:
            if self.input[line_start - 1] == '\n':
                break
            line_start -= 1
        line_end = self.input.find('\n', char)
        return (line_start, line_end)


    def error(self, line, char, type, typename, error):
        if type is None:
            type = Exception
        start, end = self.get_line_position_from_char(char)
        output  = self.input[start:end] + '\n'
        output += (' ' * (char - start)) + '^\n'
        output += '%s in line %s' % (error, line)
        raise type, 'Exscript: ' + typename  + ':\n' + output + '\n'


    def syntax_error(self, sender, error):
        self.error(sender.line, sender.char, None, 'Syntax error', error)


    def generic_error(self, sender, typename, error):
        self.error(sender.line, sender.char, None, typename, error)


    def exception(self, sender, type, typename, error):
        self.error(sender.line, sender.char, type, typename, error)


    def runtime_error(self, sender, error):
        self.generic_error(sender, 'Runtime error', error)


    def execute(self):
        return self.value()
