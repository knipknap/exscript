class Token:
    def __init__(self, name, parser):
        self.name   = name
        #self.parser = parser
        self.line   = parser.current_line
        self.char   = parser.last_char

    def value(self):
        raise Exception, "Abstract method, not implemented" #FIXME: Mark abstract

    def dump(self, indent = 0):
        print (' ' * indent) + self.name
