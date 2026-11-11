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
The base class for the tokens of a parse tree.
"""

from collections.abc import Callable
from typing import Any

from .lexer import Lexer


class Token:
    """
    Abstract base class for all tokens.
    """

    class Iterator:
        """
        A tree iterator that walks through all tokens.
        """

        def __init__(self, current: 'Token') -> None:
            """
            Constructor.

            :param current: The token at which the iteration starts.
            """
            self.path = [current]

        def __iter__(self) -> 'Token.Iterator':
            return self

        def _next(self) -> 'Token':
            """
            Returns the current token and moves on to the next token in
            depth-first order. Raises StopIteration at the end of the tree.
            """
            # Make sure that the end is not yet reached.
            if len(self.path) == 0:
                raise StopIteration()

            # If the current token has children, the first child is the next
            # item.
            current = self.path[-1]
            children = current.get_children()
            if len(children) > 0:
                self.path.append(children[0])
                return current

            # Ending up here, this task has no children. Crop the path until we
            # reach a task that has unvisited children, or until we hit the
            # end.
            while True:
                old_child = self.path.pop(-1)
                if len(self.path) == 0:
                    break

                # If this task has a sibling, choose it.
                parent = self.path[-1]
                children = parent.get_children()
                pos = children.index(old_child)
                if len(children) > pos + 1:
                    self.path.append(children[pos + 1])
                    break
            return current

        def __next__(self) -> 'Token':
            # By using this loop we avoid an (expensive) recursive call.
            while True:
                next = self._next()
                if next is not None:
                    return next

    # The parser and the parent are Any: the application defines them, and
    # parselib only stores them. The interpreter passes its Parser and a Scope.
    def __init__(self, name: str, lexer: Lexer, parser: Any, parent: Any = None) -> None:
        """
        Constructor. The marks of the new token span the character at the
        current position of the lexer.

        :param name: The name of the token, shown by dump().
        :param lexer: The lexer that reads the input.
        :param parser: The parser that builds the parse tree.
        :param parent: The parent of the token, or None.
        """
        self.lexer = lexer
        self.parser = parser
        self.parent = parent
        self.name = name
        self.children: list[Token] = []
        self.start = lexer.current_char
        self.end = lexer.current_char + 1

    # The context and the value are Any: the application defines them. The
    # value of a token depends on its class.
    def value(self, context: Any) -> Any:
        """
        Evaluates the children of the token in the given context. Subclasses
        return the value of the token.

        :param context: The context in which the token is evaluated.
        """
        for child in self.get_children():
            child.value(context)

    def mark_start(self, char: int | None = None) -> None:
        """
        Moves the start mark of the token to the given position, or to the
        current position of the lexer. If the end mark is not behind the new
        start mark, the end mark is moved one character behind it.

        :param char: The position of the first character of the token.
        """
        if char is None:
            char = self.lexer.current_char
        # EOF will point behind the last character index (length of input)!
        self.start = max(0, min(char, self.lexer.input_length))
        if self.start >= self.end:
            self.mark_end(distance=1)

    def mark_end(
        self, char: int | None = None, distance: int | None = None, rstrip: bool | str = False
    ) -> None:
        """
        Moves the end mark of the token to the given position, to the given
        distance from the start mark, or to the current position of the
        lexer. Raises ValueError if both char and distance are given.

        :param char: The position behind the last character of the token.
        :param distance: The length of the token.
        :param rstrip: Whether to move the end mark back over trailing
            whitespace. A string moves it back over the characters in it
            instead.
        """
        if char is not None and distance is not None:
            msg = 'must not specify both arguments "char" and "distance"'
            raise ValueError(msg)
        if distance is not None:
            char = self.start + distance
        elif char is None:
            char = self.lexer.current_char
        # The rstrip flag emulates the str.rstrip block per char to rewind the end mark
        # to the last non-whitespace character. This is useful when the end mark is set
        # at the end of a Token init, that finally skipped trailing whitespaces.
        if rstrip:
            if isinstance(rstrip, str):
                isspace: Callable[[str], bool] = lambda c: c in rstrip  # noqa: E731
            else:
                isspace = lambda c: c.isspace()  # noqa: E731
            while char > 0 and isspace(self.lexer.input[char - 1 : char]):
                char -= 1
        # EOF will point behind the last character index (length of input)!
        self.end = max(self.start, min(char, self.lexer.input_length))

    def __iter__(self) -> 'Token.Iterator':
        """
        Returns an iterator that points to the first token.
        """
        return Token.Iterator(self)

    def add(self, child: 'Token') -> None:
        """
        Appends the given token to the children of this token.
        """
        self.children.append(child)

    def get_children(self) -> list['Token']:
        """
        Returns the children of this token.
        """
        return self.children

    def dump(self, indent: int = 0) -> None:
        """
        Prints the name of the token to stdout, followed by a dump of each
        child with one more level of indentation.

        :param indent: The indentation of this token.
        """
        print((' ' * indent) + self.name)
        for child in self.get_children():
            child.dump(indent + 1)
