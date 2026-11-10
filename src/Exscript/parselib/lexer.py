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
"""
A lexer that splits its input into tokens with regular expressions.
"""

import re
import warnings
from collections.abc import Callable, Sequence
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast

from .exception import CompileError, CompileWarning, ExecuteError, LexerException

if TYPE_CHECKING:
    from .token import Token


class Lexer:
    """
    Splits its input into tokens with a stack of grammars, and reports
    errors with their position in the input. A grammar is a sequence of
    (token type, compiled regular expression) pairs: the first pair whose
    expression matches at the current position defines the current token.
    The parser class that is passed to the constructor reads the tokens and
    builds the parse tree.
    """

    def __init__(self, parser_cls: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        """
        Constructor. The given args are passed to the parser_cls constructor.

        :param parser_cls: The class that parse() calls with this lexer and
            the given args; it returns the parse result.
        :param kwargs: ``debug``: with a value of 5 or more, parse() dumps
            the parse result to stdout.
        """
        self.parser_cls = parser_cls
        self.parser_cls_args = args
        self.filename: str | None = None
        self.input = ''
        self.input_length = 0
        self.current_char = 0
        self.last_char = 0
        self.token_buffer: tuple[str, str] | None = None
        self.grammar: list[Sequence[tuple[str, re.Pattern[str]]]] = []
        self.debug: int = kwargs.get('debug', False)

    def set_grammar(self, grammar: Sequence[tuple[str, re.Pattern[str]]]) -> None:
        """
        Pushes the given grammar onto the stack of grammars, so that it
        becomes the current grammar.

        :param grammar: (token type, compiled regular expression) pairs, in
            the order in which they are tried.
        """
        self.grammar.append(grammar)
        self.token_buffer = None

    def restore_grammar(self) -> None:
        """
        Removes the current grammar from the stack of grammars, so that the
        previous grammar becomes current again.
        """
        self.grammar.pop()
        self.token_buffer = None

    def match(self) -> None:
        """
        Finds the token at the current position with the current grammar and
        stores its type and text in the token buffer. At the end of the
        input, the token is ('EOF', ''). Raises a CompileError if no
        expression of the grammar matches.
        """
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
        # prevent cutoffs in the middle of a word/line. Without a blank or the
        # end of the input within 50 characters, show all 50.
        regex = re.compile(r'.{1,50}(?=[ \t\r\n]|$)', flags=re.S)
        match = regex.match(self.input, sender.start)
        if match is None:
            context = self.input[sender.start : sender.start + 50]
        else:
            context = match.group(0)
        error = 'Invalid syntax: %s' % repr(context)
        self.syntax_error(error, sender)

    def _get_line_number_from_char(self, char: int) -> int:
        """
        Returns the number (counted from 1) of the line that contains the
        given position.
        """
        return self.input[:char].count('\n') + 1

    def get_current_line_number(self) -> int:
        """
        Returns the number (counted from 1) of the line at the current
        position.
        """
        return self._get_line_number_from_char(self.current_char)

    def _get_line(self, number: int) -> str:
        """
        Returns the line with the given number (counted from 1), without
        the newline.
        """
        return self.input.split('\n')[number - 1]

    def _get_lines(self, first: int, last: int) -> list[str]:
        """
        Returns the lines from the first to the last given number (counted
        from 1, both included), without the newlines.
        """
        return self.input.split('\n')[first - 1 : last]

    def get_current_line(self) -> str:
        """
        Returns the line at the current position, without the newline.
        """
        line = self.get_current_line_number()
        return self._get_line(line)

    def _get_line_from_char(self, char: int) -> str:
        """
        Returns the line that contains the given position, without the
        newline.
        """
        line = self._get_line_number_from_char(char)
        return self._get_line(line)

    def _get_line_position_from_char(self, char: int) -> tuple[int, int]:
        """
        Returns the position of the first character of the line that
        contains the given position, and the position of the newline that
        ends the line (or the length of the input).
        """
        line_start = char
        while line_start != 0:
            if self.input[line_start - 1] == '\n':
                break
            line_start -= 1
        line_end = self.input.find('\n', char)
        if line_end == -1:
            line_end = self.input_length
        return line_start, line_end

    def _error(
        self, exc_cls: type[Exception], error: str, sender: 'Token | SimpleNamespace | None' = None
    ) -> None:
        """
        Raises an exception of the given class with the given message, or
        emits it as a warning if the class is a Warning. If a sender is given,
        the message also shows the lines of the input that the sender marks,
        with the marked range underlined, and the file name and line
        number(s).
        """
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
                # The pattern also matches an empty string, so it always matches.
                offset = min(offset, len(cast(re.Match[str], whitespace_re.match(ln)).group(0)))
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

    def error(
        self,
        error: str,
        sender: 'Token | SimpleNamespace | None' = None,
        exc_cls: type[Exception] = LexerException,
    ) -> None:
        """
        Raises an exception of the given class with the given message, or
        emits it as a warning if the class is a Warning. The message shows
        the position of the sender, as described in syntax_error().

        :param error: The error message.
        :param sender: The token that caused the error.
        :param exc_cls: The exception class.
        """
        self._error(exc_cls, error, sender)

    def syntax_error(self, error: str, sender: 'Token | SimpleNamespace | None' = None) -> None:
        """
        Raises a CompileError with the given message. If a sender is given,
        the message also shows the lines of the input that the sender marks,
        with the marked range underlined, and the file name and line
        number(s).

        :param error: The error message.
        :param sender: The token that caused the error.
        """
        self._error(CompileError, error, sender)

    def syntax_warning(self, warning: str, sender: 'Token | SimpleNamespace | None' = None) -> None:
        """
        Emits a CompileWarning with the given message, which shows the
        position of the sender as described in syntax_error().

        :param warning: The warning message.
        :param sender: The token that caused the warning.
        """
        self._error(CompileWarning, warning, sender)

    def runtime_error(self, error: str, sender: 'Token | SimpleNamespace | None' = None) -> None:
        """
        Raises an ExecuteError with the given message, which shows the
        position of the sender as described in syntax_error().

        :param error: The error message.
        :param sender: The token that caused the error.
        """
        self._error(ExecuteError, error, sender)

    def forward(self, chars: int = 1) -> None:
        """
        Moves the current position forward by the given number of
        characters, and remembers the previous position in last_char.
        """
        self.last_char = self.current_char
        self.current_char += chars
        self.token_buffer = None

    def __next__(self) -> None:
        if self.token_buffer:
            if self.token_buffer[0] == 'EOF':
                msg = "Unexpected EOF while iterating tokens."
                raise StopIteration(msg)
            self.forward(len(self.token_buffer[1]))

    def next_if(self, types: str | list[str], token: str | None = None) -> int:
        """
        Moves past the current token if it has one of the given types and,
        if a token text is given, that text.

        :param types: A token type, or a list of token types.
        :param token: The text that the token must have.
        :return: 1 if the lexer moved past the token, 0 otherwise.
        """
        if type(types) is not type([]):
            types = [cast(str, types)]
        if self.current_is(types, token):
            next(self)
            return 1
        return 0

    def skip(self, types: str | list[str], token: str | None = None) -> None:
        """
        Moves past consecutive tokens that have one of the given types and,
        if a token text is given, that text.

        :param types: A token type, or a list of token types.
        :param token: The text that the tokens must have.
        """
        while self.next_if(types, token):
            pass

    def expect(self, sender: 'Token', types: str | list[str], token: str | None = None) -> None:
        """
        Moves past the current token if it has one of the given types and,
        if a token text is given, that text. Otherwise, moves the marks of
        the sender to the current token and raises a CompileError.

        :param sender: The token that expects the token.
        :param types: A token type, or a list of token types.
        :param token: The text that the token must have.
        """
        cur_type, cur_token = self.token()
        if type(types) is not type([]):
            types = [cast(str, types)]
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

    def current_is(self, types: str | list[str], token: str | None = None) -> int:
        """
        Returns whether the current token has one of the given types and, if
        a token text is given, that text.

        :param types: A token type, or a list of token types.
        :param token: The text that the token must have.
        :return: 1 if the token matches, 0 otherwise.
        """
        if self.token_buffer is None:
            self.match()
        if type(types) is not type([]):
            types = [cast(str, types)]
        # match() fills the token buffer or raises an error.
        if cast(tuple[str, str], self.token_buffer)[0] not in types:
            return 0
        if token is None or cast(tuple[str, str], self.token_buffer)[1] == token:
            return 1
        return 0

    def token(self) -> tuple[str, str]:
        """
        Returns the type and the text of the current token.
        """
        if self.token_buffer is None:
            self.match()
        # match() fills the token buffer or raises an error.
        return cast(tuple[str, str], self.token_buffer)

    # The parse result is Any: the parser class defines it.
    def parse(self, string: str, filename: str | None = None) -> Any:
        """
        Resets the lexer to the given input and parses it: calls the parser
        class with this lexer and the args that were passed to the
        constructor.

        :param string: The input.
        :param filename: The file name that error messages show.
        :return: The object that the parser class returns.
        """
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

    def parse_file(self, filename: str) -> Any:
        """
        Like parse(), but reads the input from the given UTF-8 file.

        :param filename: The name of the file.
        :return: The object that the parser class returns.
        """
        with open(filename, encoding='utf-8') as fp:
            return self.parse(fp.read(), filename)
