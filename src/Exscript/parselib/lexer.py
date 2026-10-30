#
# Copyright (C) 2010-2017 Samuel Abels
# The MIT License (MIT)
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
import re
import warnings
from types import SimpleNamespace

from .exception import CompileError, CompileWarning, ExecuteError, LexerException


class Lexer:
    def __init__(self, parser_cls, *args, **kwargs):
        """
        The given args are passed to the parser_cls constructor.
        """
        self.parser_cls = parser_cls
        self.parser_cls_args = args
        self.filename = None
        self.input = ''
        self.input_length = 0
        self.current_char = 0
        self.last_char = 0
        self.token_buffer = None
        self.grammar = []
        self.debug = kwargs.get('debug', False)

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
        for token_type, token_regex in self.grammar[-1]:
            match = token_regex.match(self.input, self.current_char)
            if match is not None:
                self.token_buffer = (token_type, match.group(0))
                # print("Match:", self.token_buffer)
                return
        # The match failed so we raise an invalid syntax error. We create a fake
        # sender object with marks to reuse the existing error handling code.
        sender = SimpleNamespace(start=self.current_char, end=self.current_char + 1)
        # Match 1..50 chars (eager) up to the last space, newline or EOF to
        # prevent cutoffs in the middle of a word/line.
        regex = re.compile(r'.{1,50}(?=[ \t\r\n]|$)', flags=re.S)
        context = regex.match(self.input, sender.start).group(0)
        error = 'Invalid syntax: %s' % repr(context)
        self.syntax_error(error, sender)

    def _get_line_number_from_char(self, char):
        return self.input[:char].count('\n') + 1

    def get_current_line_number(self):
        return self._get_line_number_from_char(self.current_char)

    def _get_line(self, number):
        return self.input.split('\n')[number - 1]

    def _get_lines(self, first, last):
        return self.input.split('\n')[first - 1 : last]

    def get_current_line(self):
        line = self.get_current_line_number()
        return self._get_line(line)

    def _get_line_from_char(self, char):
        line = self._get_line_number_from_char(char)
        return self._get_line(line)

    def _get_line_position_from_char(self, char):
        line_start = char
        while line_start != 0:
            if self.input[line_start - 1] == '\n':
                break
            line_start -= 1
        line_end = self.input.find('\n', char)
        if line_end == -1:
            line_end = self.input_length
        return line_start, line_end

    def _error(self, exc_cls, error, sender=None):
        if not sender:
            if issubclass(exc_cls, Warning):
                warnings.warn(exc_cls('\n' + error), stacklevel=3)
                return
            raise exc_cls('\n' + error)
        lineno_first = self._get_line_number_from_char(sender.start)
        lineno_last = self._get_line_number_from_char(sender.end)
        # When the sender marks a range, that ends with a newline character, the
        # end mark would point to an additional irrelevant line, so we fix that.
        if self.input[sender.start : sender.end].endswith('\n'):
            lineno_last -= 1
        lines = self._get_lines(lineno_first, lineno_last)

        # Determine the offset and width of the offending range.
        if len(lines) <= 1:
            # Use the sender's start/end marks for single-line ranges. The sender
            # is responsible to set the correct marks (no adjustments here).
            lineno = str(lineno_first)
            offset = sender.start - self._get_line_position_from_char(sender.start)[0]
            token_length = sender.end - sender.start
        else:
            # Multiline ranges are more complicated so the min. offset on the left and
            # max. width to the right need to be calculated from all non-empty lines.
            lineno = '%s-%s' % (lineno_first, lineno_last)
            offset = self.input_length  # reasonable high starting value
            token_length = 1  # reasonable low starting value
            whitespace_re = re.compile(r'[ \t]*')
            for ln in lines:
                if ln.strip() == '':
                    continue
                offset = min(offset, len(whitespace_re.match(ln).group(0)))
                token_length = max(token_length, len(ln.rstrip()))
            token_length -= offset

        # Build the error string with the offending line(s).
        output = '\n'.join(lines) + '\n'
        if token_length <= 1:
            output += (' ' * offset) + '^\n'
        else:
            output += (' ' * offset) + ('^' * token_length) + '\n'
        output += '%s in %s:%s' % (error, self.filename, lineno)
        if issubclass(exc_cls, Warning):
            warnings.warn(exc_cls('\n' + output), stacklevel=3)
            return
        raise exc_cls('\n' + output)

    def error(self, error, sender=None, exc_cls=LexerException):
        self._error(exc_cls, error, sender)

    def syntax_error(self, error, sender=None):
        self._error(CompileError, error, sender)

    def syntax_warning(self, warning, sender=None):
        self._error(CompileWarning, warning, sender)

    def runtime_error(self, error, sender=None):
        self._error(ExecuteError, error, sender)

    def forward(self, chars=1):
        self.last_char = self.current_char
        self.current_char += chars
        self.token_buffer = None

    def __next__(self):
        if self.token_buffer:
            if self.token_buffer[0] == 'EOF':
                msg = "Unexpected EOF while iterating tokens."
                raise StopIteration(msg)
            self.forward(len(self.token_buffer[1]))

    def next_if(self, types, token=None):
        if type(types) is not type([]):
            types = [types]
        if self.current_is(types, token):
            next(self)
            return 1
        return 0

    def skip(self, types, token=None):
        while self.next_if(types, token):
            pass

    def expect(self, sender, types, token=None):
        cur_type, cur_token = self.token()
        if type(types) is not type([]):
            types = [types]
        if self.next_if(types, token):
            return
        if token:
            error = 'Expected %s but got %s %s'
            error = error % (repr(token), cur_type, repr(cur_token))
        elif len(types) > 1:
            error = 'Expected one of %s but got %s %s'
            error = error % (', '.join(types), cur_type, repr(cur_token))
        else:
            error = 'Expected %s but got %s %s'
            error = error % (types[0], cur_type, repr(cur_token))
        # In this case we do not point to the token that raised the error,
        # but to the actual position of the lexer.
        sender.start = self.current_char
        sender.end = self.current_char + len(cur_token)
        self.syntax_error(error, sender)

    def current_is(self, types, token=None):
        if self.token_buffer is None:
            self.match()
        if type(types) is not type([]):
            types = [types]
        if self.token_buffer[0] not in types:
            return 0
        if token is None or self.token_buffer[1] == token:
            return 1
        return 0

    def token(self):
        if self.token_buffer is None:
            self.match()
        return self.token_buffer

    def parse(self, string, filename=None):
        # Re-initialize, so that the same lexer instance may be used multiple
        # times.
        self.filename = filename
        self.input = string
        self.input_length = len(string)
        self.current_char = 0
        self.last_char = 0
        self.token_buffer = None
        self.grammar = []
        compiled = self.parser_cls(self, *self.parser_cls_args)
        if self.debug >= 5:
            # IDEA: Consider to switch compiled.dump() from print() to logging.
            #  The related code is located in Exscript.interpreter.*.dump() methods.
            compiled.dump()
        return compiled

    def parse_file(self, filename):
        with open(filename) as fp:
            return self.parse(fp.read(), filename)
