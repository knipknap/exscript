# Copyright (C) 2007 Samuel Abels, http://debain.org
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import copy
import types
import stdlib
from Program import Program

class Parser(object):
    def __init__(self, *args, **kwargs):
        self.input        = ''
        self.input_length = 0
        self.current_char = 0
        self.last_char    = 0
        self.current_line = 1
        self.token_buffer = None
        self.grammar      = []
        self.debug        = kwargs.get('debug', 0)
        self.variables    = {}
        self.stdlib       = {}
        self.load_module(stdlib)


    def define(self, **kwargs):
        for key in kwargs:
            if type(kwargs[key]) == type([]):
                self.variables[key] = kwargs[key]
            else:
                self.variables[key] = [kwargs[key]]


    def define_function(self, **kwargs):
        self.variables.update(kwargs)


    def load_module(self, module):
        if self.debug > 0:
            print 'Loading module', module.__name__
        for name in module.__dict__['__all__']:
            if name.startswith('_'):
                continue
            mod_name  = module.__name__[module.__name__.index('.') + 1:]
            item_name = mod_name + '.' + name
            item      = __import__(item_name, globals(), locals(), [mod_name])
            if not 'execute' in dir(item):
                self.load_module(item)
                continue
            func_name = item_name + '.execute'
            item_name = item_name[item_name.index('.') + 1:].lower()
            if self.debug > 1:
                print 'Loaded function', item_name
            self.stdlib[item_name] = item.__dict__['execute']


    def set_grammar(self, grammar):
        self.grammar.append(grammar)
        self.token_buffer = None


    def restore_grammar(self):
        self.grammar.pop()
        self.token_buffer = None


    def match(self):
        if self.current_char >= self.input_length:
            self.token_buffer = ('EOF', '')
            return
        for type, regex in self.grammar[-1]:
            match = regex.match(self.input, self.current_char)
            if match is not None:
                self.token_buffer = (type, match.group(0))
                #print "Match:", self.token_buffer
                return
        self.syntax_error('Invalid syntax: %s' % self.input[self.current_char:])


    def syntax_error(self, error):
        raise Exception, error


    def next(self):
        #print "Old:", repr(self.input[self.current_char:])
        self.last_char     = self.current_char
        self.current_char += len(self.token_buffer[1])
        #print "New:", repr(self.input[self.current_char:])
        if self.token_buffer[0] == 'newline':
            self.current_line += 1
            #print "Line:", self.current_line
        self.token_buffer = None


    def next_if(self, type, token = None):
        if not self.current_is(type, token):
            return 0
        self.next()
        return 1


    def expect(self, sender, type, token = None):
        (cur_type, cur_token) = self.token()
        if not self.next_if(type, token):
            if token is None:
                error = 'Expected %s but got %s' % (type, cur_token)
            else:
                error = 'Expected "%s" but got "%s"' % (token, cur_token)
            sender.char = self.current_char
            sender.parent.syntax_error(sender, error)
        return 1


    def current_is(self, type, token = None):
        if self.token_buffer is None:
            self.match()
        if self.token_buffer[0] != type:
            return 0
        if token is None:
            return 1
        if self.token_buffer[1] == token:
            return 1
        return 0


    def token(self):
        if self.token_buffer is None:
            self.match()
        return self.token_buffer


    def parse(self, string):
        # Re-initialize variables, so that the same parser instance may be used multiple
        # times.
        self.input        = string
        self.input_length = len(string)
        self.current_char = 0
        self.last_char    = 0
        self.current_line = 0
        self.token_buffer = None
        self.grammar      = []

        # Define the standard library now, in order to prevent it from being overwritten
        # by the user.
        variables = copy.deepcopy(self.variables)
        variables.update(self.stdlib)
        compiled = Program(self, None, variables = variables)
        if self.debug > 3:
            compiled.dump()
        return compiled


    def parse_file(self, filename):
        file   = open(filename)
        string = file.read()
        file.close()
        return self.parse(string)


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 1:
        filename = 'test.exscript'
    elif len(sys.argv) == 2:
        filename = sys.argv[1]
    else:
        sys.exit(1)
    parser   = Parser()
    compiled = parser.parse_file(filename)
    compiled.dump()
