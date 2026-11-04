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
The commands of a template, which are sent to the remote host.
"""

import re
import textwrap
from typing import TYPE_CHECKING, cast

from ..parselib import Lexer, Token
from ..util.xml import validate_xml
from .scope import Scope
from .string import String, varstring_re

if TYPE_CHECKING:
    from .parser import Parser

grammar = {
    'leading_blank_lines': r'^(?:[ \t]*[\r\n])+',
    'trailing_blank_lines': r'(?:[\r\n][ \t]*)+$',
    'line_comment': r'(?:^|(?<=[\r\n]))[ \t]*#[^\r\n]*(?:[\r\n]|$)',
}
leading_whitespace_re = re.compile(r'^[ \t\r\n]*')
line_comment_re = re.compile(grammar['line_comment'])
strip_re = re.compile('|'.join(grammar.values()))


class Execute(String):
    """
    A command that is sent to the remote host. Variables in the command
    ($name) are replaced by their values when the command is sent, and the
    response of the host is stored in the __response__ variable.
    """

    def __init__(
        self, lexer: Lexer, parser: 'Parser', parent: Scope, command: str, escape_offset: int = 0
    ) -> None:
        """
        Constructor. Checks that the variables in the command are defined,
        and declares the __response__ variable. In an <rpc> element, it also
        checks the XML syntax of the command: an error raises a
        CompileError, or emits a CompileWarning if the command contains
        variables.

        :param lexer: The lexer that reads the template, positioned behind
            the command.
        :param parser: The parser of the template.
        :param parent: The scope that contains the command.
        :param command: The command as read from the template.
        :param escape_offset: The number of characters by which the
            evaluation of escape sequences shortened the command, for the
            position of the command in error messages.
        """
        Token.__init__(self, self.__class__.__name__, lexer, parser, parent)
        self.delimiter = ''  # Command strings are not delimited in Execute tokens.
        self.string = command  # Original command will be evaluated at runtime.
        self.no_prompt = parser.no_prompt
        self.strip_command = parser.strip_command

        # The lexer has parsed the command and consumed the trailing command delimiter
        # (newline, open curly bracket, RPC tag). We want the debugger point to the
        # beginning of the command. The offset is expected to be the length of the
        # additionally consumed command delimiter before entering this Execute token.
        # Any offset caused by prior escape evaluation is also taken into account.
        command = command.lstrip()
        delimiter_offset = lexer.current_char - lexer.last_char
        self.mark_start(self.start - len(command) - delimiter_offset - escape_offset)
        self.mark_end(distance=len(command.strip()) + escape_offset)

        # Make sure that any variables specified in the command are declared.
        # Once more we use the left-stripped command to align with the start mark.
        # NOTE: The substitution test might also fire in line comments with variables.
        #  This is prevented by making the line comments "invisible" while preserving
        #  the overall command length/structure for proper error tracking.
        command = line_comment_re.sub(self.invisible_sub_cb, command)
        varstring_re.sub(self.variable_test_cb, command)

        # Validate XML for RPCBody tokens. We need to use the original command
        # string for exact reporting on UnicodeEncodeError and XMLSyntaxError.
        # Additionally we need to replace all remaining variable chars with "_"
        # to create an XML tree as valid as possible. The XML body will be
        # tested once more at runtime by the protocol adapter (evaluated vars).
        if type(parent).__name__ == 'RPCBody':
            from lxml.etree import XMLSyntaxError  # only templates with RPCs need lxml

            # The start mark points to the first non-whitespace character of the
            # RPC body. We will need the original start position of the command.
            # (The pattern also matches an empty string, so it always matches.)
            original_start = self.start - len(
                '<rpc>' + cast(re.Match[str], leading_whitespace_re.search(self.string)).group(0)
            )

            # Prepare full RPC command to eliminate most false-positives.
            rpc_command = f'<rpc>{self.string}</rpc>'
            rpc_command = line_comment_re.sub(self.invisible_sub_cb, rpc_command)
            has_vars = bool(varstring_re.search(rpc_command))
            rpc_command = varstring_re.sub(self.variable_sigil_sub_cb, rpc_command)

            # Now we can validate the prepared RPC command.
            msg = "XML validation of the RPC command has failed. The error was caused by:\n"
            try:
                validate_xml(rpc_command, silent=False)
            except UnicodeEncodeError as exc:
                # UnicodeEncodeError position (start, end) comes with a valid
                # absolute character offset. Simply adjust the start/end marks.
                self.mark_start(original_start + exc.start)
                self.mark_end(distance=(exc.end - exc.start))
                msg += f'{type(exc).__name__}: {exc}'
                lexer.syntax_error(msg, self)
            except XMLSyntaxError as exc:
                # XMLSyntaxError position (line, offset) needs to be converted
                # to an absolute character offset. Then adjust the start/end marks.
                # lxml always sets lineno and offset, which SyntaxError types as
                # int | None.
                lines = rpc_command.splitlines(keepends=True)
                exc_start = len(''.join(lines[: cast(int, exc.lineno) - 1]))
                exc_start += cast(int, exc.offset)
                # We assume the end positions are either both set or not!
                exc_end = len(''.join(lines[: (exc.end_lineno or cast(int, exc.lineno)) - 1]))
                exc_end += exc.end_offset or cast(int, exc.offset) + 1
                self.mark_start(original_start + exc_start)
                self.mark_end(distance=(exc_end - exc_start))
                if has_vars:
                    msg = (
                        "XML validation of the RPC command has failed. This could "
                        "be a real syntax error or might depend on the final variable "
                        "substitution at runtime. The warning was caused by:\n"
                    )
                    msg += f'{type(exc).__name__}: {exc}'
                    lexer.syntax_warning(msg, self)
                else:
                    msg += f'{type(exc).__name__}: {exc}'
                    lexer.syntax_error(msg, self)

        self.parent.define(__response__=[''])

    def value(self, context: Scope) -> int:
        """
        Sends the command, without line comments, surrounding blank lines
        and common indentation, and with the variables replaced by their
        values. Waits for the prompt unless the parser was created with
        no_prompt. Stores the response in the __response__ variable, one
        line per item. Raises an ExecuteError if the __connection__ variable
        is not defined.

        :param context: The scope in which the template runs.
        :return: 1.
        """
        connvar = "__connection__"
        if not self.parent.is_defined(connvar):
            error = 'Undefined variable %s' % repr(connvar)
            self.lexer.runtime_error(error, self)
        conn = self.parent.get(connvar)

        # Prepare the command for execution by stripping unwanted substrings.
        # The dedent of common indentations is useful for multiline commands.
        command = strip_re.sub('', self.string)
        command = textwrap.dedent(command)

        # Substitute variables in the command for values.
        command = varstring_re.sub(self.variable_sub_cb, command)

        # Execute the command.
        if self.no_prompt:
            conn.send(command + '\r')
        else:
            conn.execute(command)
        response = conn.get_response(strip_command=self.strip_command)
        response = response.split('\n')
        self.parent.define(__response__=response)
        return 1

    def dump(self, indent: int = 0) -> None:
        """
        Prints the command to stdout.

        :param indent: The indentation of this token.
        """
        print((' ' * indent) + self.name, repr(self.string))
