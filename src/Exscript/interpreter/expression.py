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
Expressions of the template language.
"""

import re
from typing import TYPE_CHECKING, Any, cast

import Exscript.interpreter.term

from ..parselib import Lexer, Token
from .scope import Scope

if TYPE_CHECKING:
    from .parser import Parser


# Any: the value of a term, an expression or a variable, and the items of
# the list.
def as_list(value: Any, token: Token, name: str | None = None) -> list[Any]:
    """
    Returns the given value as a list, as the operators and statements use
    it: a list as it is, a tuple as a list, and any other value, such as the
    True that a function returns without a result, as a list with this one
    item. Raises an ExecuteError at the given token if the value is a
    regular expression or a function.

    :param value: The value.
    :param token: The term or the expression whose value it is, or the
        statement that reads it from a variable.
    :param name: The name of the variable for the error message about a
        function; by default the text of the token.
    """
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, re.Pattern):
        msg = "A regular expression is only allowed as the right operand of 'matches'"
        token.lexer.runtime_error(msg, token)
    if callable(value):
        if name is None:
            name = token.lexer.input[token.start : token.end]
        token.lexer.runtime_error('%s is a function, not a variable name' % repr(name), token)
    return [value]


class ExpressionNode(Token):
    """
    A node of an expression. The constructor parses a chain of nodes: a
    term, optionally followed by an operator and the rest of the expression
    as the right-hand node; a node that starts with "not" has no term.
    Expression.prioritize() turns the chain into a tree, in which the
    left-hand and right-hand nodes are the operands of the operator.
    """

    def __init__(self, lexer: Lexer, parser: 'Parser', parent: Scope) -> None:
        """
        Constructor. Parses a term and, if an operator follows, the operator
        and the rest of the expression.

        :param lexer: The lexer that reads the template.
        :param parser: The parser of the template.
        :param parent: The scope that contains the expression.
        """
        # Skip whitespace before initializing the token to make sure that self.start
        # points to the beginning of the expression (which makes for prettier error
        # messages).
        lexer.skip(['whitespace', 'newline'])

        Token.__init__(self, self.__class__.__name__, lexer, parser, parent)
        self.lft: Exscript.interpreter.term.Term | ExpressionNode | None = None
        self.rgt: Exscript.interpreter.term.Term | ExpressionNode | None = None
        self.op = None
        self.op_type = None

        # The "not" operator requires special treatment because it is
        # positioned left of the term.
        if not lexer.current_is('logical_operator', 'not'):
            self.lft = Exscript.interpreter.term.Term(lexer, parser, parent)

            # The expression may end already (a single term is also an expression).
            lexer.skip(['whitespace', 'newline'])
            if (
                not lexer.current_is('arithmetic_operator')
                and not lexer.current_is('logical_operator')
                and not lexer.current_is('comparison')
                and not lexer.current_is('regex_delimiter')
            ):
                # Early end of statement.
                self.mark_end(rstrip=True)
                return

        # Expect the operator.
        self.op_type, self.op = lexer.token()
        if (
            not lexer.next_if('arithmetic_operator')
            and not lexer.next_if('logical_operator')
            and not lexer.next_if('comparison')
            and not lexer.next_if('regex_delimiter')
        ):
            self.mark_start()
            self.mark_end(distance=len(self.op))
            msg = 'Expected operator but got %s %s' % (self.op_type, repr(self.op))
            lexer.syntax_error(msg, self)
        # The words of "is not" and "not in" may be separated by any whitespace.
        self.op = ' '.join(self.op.split())

        # Expect the second term.
        self.rgt = ExpressionNode(lexer, parser, parent)
        # End of statement.
        self.mark_end(rstrip=True)

    def priority(self) -> int:
        """
        Returns the priority of the operator of the node, from 1 for "and"
        and "or" to 6 for "*", "/" and "%", or 8 if the node has no operator.
        Raises an Exception for an unknown operator.
        """
        if self.op is None:
            return 8
        elif self.op_type == 'arithmetic_operator' and self.op in ('*', '%'):
            return 6
        elif self.op_type == 'regex_delimiter':
            return 6
        elif self.op_type == 'arithmetic_operator' and self.op != '.':
            return 5
        elif self.op == '.':
            return 4
        elif self.op_type == 'comparison':
            return 3
        elif self.op == 'not':
            return 2
        elif self.op_type == 'logical_operator':
            return 1
        else:
            raise Exception('Invalid operator: ' + repr(self.op))

    # Any: the value of a term, or a list with the result of the operator.
    def value(self, context: Scope) -> Any:
        """
        Evaluates the node. An operand is used as a list, see as_list(), and
        stands for its first item, or '' if it is empty. "and" and "or"
        evaluate the right operand only if the left one does not decide the
        result. Arithmetic operators and ge, gt, le and lt raise an
        ExecuteError if an operand is not a number, and / and % if the right
        operand is 0. A regular expression raises an ExecuteError unless it
        is the right operand of "matches".

        :param context: The scope in which the template runs.
        :return: The value of the term if the node has no operator, or a
            list with the result of the operator.
        """
        # The operator decides which operands are set: lft is set unless the
        # operator is "not", and rgt is set if there is an operator.
        # Special behavior where we only have one term.
        if self.op is None:
            return cast(Token, self.lft).value(context)
        elif self.op == 'not':
            rgt_lst = cast(Token, self.rgt).value(context)
            rgt_lst = as_list(rgt_lst, cast(Token, self.rgt))
            return [not (rgt_lst[0] if len(rgt_lst) > 0 else '')]

        # The operands are lists, except the regular expression on the right of
        # "matches". We also have to make sure that empty lists do not cause an
        # error. The first item of a list can be a string, a number or anything
        # else that a function returned, hence Any.
        lft_lst = as_list(cast(Token, self.lft).value(context), cast(Token, self.lft))
        lft: Any = lft_lst[0] if len(lft_lst) > 0 else ''
        # The left operand of "and" and "or" may decide the result alone.
        if (self.op == 'and' and not lft) or (self.op == 'or' and lft):
            return [lft]
        rgt_lst = cast(Token, self.rgt).value(context)
        if self.op != 'matches':
            rgt_lst = as_list(rgt_lst, cast(Token, self.rgt))
        rgt: Any = rgt_lst[0] if isinstance(rgt_lst, list) and len(rgt_lst) > 0 else ''

        if self.op in ('*', '/', '%', '+', '-', 'ge', 'gt', 'le', 'lt'):
            error = 'Operand for %s is not a number' % (self.op)
            try:
                lft = int(lft)
            except (TypeError, ValueError):
                self.lexer.runtime_error(error, self.lft)
            try:
                rgt = int(rgt)
            except (TypeError, ValueError):
                self.lexer.runtime_error(error, self.rgt)
            if self.op in ('/', '%') and rgt == 0:
                self.lexer.runtime_error('Division by zero', self.rgt)

        # Two-term expressions.
        if self.op == 'is':
            return [lft == rgt]
        elif self.op == 'matches':
            regex = rgt_lst
            # The "matches" keyword requires a regular expression as the right hand
            # operand. The exception throws if "regex" does not have a match()
            # method.
            try:
                regex.match(str(lft))
            except AttributeError:
                error = 'Right hand operator is not a regular expression'
                self.lexer.runtime_error(error, self.rgt)
            for line in lft_lst:
                if regex.search(str(line)):
                    return [1]
            return [0]
        elif self.op == 'is not':
            # print("LFT: '%s', RGT: '%s', RES: %s" % (lft, rgt, [lft != rgt]))
            return [lft != rgt]
        elif self.op == 'in':
            return [lft in rgt_lst]
        elif self.op == 'not in':
            return [lft not in rgt_lst]
        elif self.op == 'ge':
            return [int(lft) >= int(rgt)]
        elif self.op == 'gt':
            return [int(lft) > int(rgt)]
        elif self.op == 'le':
            return [int(lft) <= int(rgt)]
        elif self.op == 'lt':
            return [int(lft) < int(rgt)]
        elif self.op == 'and':
            return [lft and rgt]
        elif self.op == 'or':
            return [lft or rgt]
        elif self.op == '*':
            return [int(lft) * int(rgt)]
        elif self.op == '/':
            return [int(lft) // int(rgt)]
        elif self.op == '%':
            return [int(lft) % int(rgt)]
        elif self.op == '.':
            return [str(lft) + str(rgt)]
        elif self.op == '+':
            return [int(lft) + int(rgt)]
        elif self.op == '-':
            return [int(lft) - int(rgt)]

    def dump(self, indent: int = 0) -> None:
        """
        Prints the node, its operator and its operands to stdout.

        :param indent: The indentation of this token.
        """
        print((' ' * indent) + self.name, self.op, 'start')
        if self.lft is not None:
            self.lft.dump(indent + 1)
        print((' ' * (indent + 1)) + 'Operator', self.op)
        if self.rgt is not None:
            self.rgt.dump(indent + 1)
        print((' ' * indent) + self.name, self.op, 'end')


class Expression(Token):
    """
    An expression: a tree of ExpressionNode objects, ordered by the priority
    of the operators.
    """

    def __init__(self, lexer: Lexer, parser: 'Parser', parent: Scope) -> None:
        """
        Constructor. Parses the expression and orders its nodes by the
        priority of the operators.

        :param lexer: The lexer that reads the template.
        :param parser: The parser of the template.
        :param parent: The scope that contains the expression.
        """
        Token.__init__(self, self.__class__.__name__, lexer, parser, parent)

        # Parse the expression, and order the nodes by the operator priorities.
        self.root = self.prioritize(ExpressionNode(lexer, parser, parent))

        # End of statement.
        self.mark_end(rstrip=True)

    def prioritize(
        self, start: ExpressionNode
    ) -> 'Exscript.interpreter.term.Term | ExpressionNode':
        """
        Turns the chain of nodes that the parser created into a tree, in
        which the operators with a higher priority take their operands
        first, and operators with the same priority from left to right. A
        "not" takes the expression up to the next operator whose priority is
        not higher than its own. The marks of each node span its operands.

        :param start: The first node of the chain.
        :return: The root of the tree.
        """
        operands: list[Exscript.interpreter.term.Term | ExpressionNode] = []
        operators: list[ExpressionNode] = []

        def reduce() -> None:
            # Gives the last operator its operands, and makes it an operand.
            node = operators.pop()
            node.rgt = operands.pop()
            if node.op != 'not':
                node.lft = operands.pop()
                node.mark_start(node.lft.start)
            node.mark_end(node.rgt.end)
            operands.append(node)

        node: ExpressionNode | None = start
        while node is not None:
            # In the chain, the right-hand node of a node is the next node.
            following = cast('ExpressionNode | None', node.rgt)
            if node.op is None:
                operands.append(node)
            else:
                if node.op != 'not':
                    # The parser gives the nodes with a binary operator a term.
                    operands.append(cast(Exscript.interpreter.term.Term, node.lft))
                    while operators and operators[-1].priority() >= node.priority():
                        reduce()
                operators.append(node)
            node = following
        while operators:
            reduce()
        return operands[0]

    # Any: see ExpressionNode.value().
    def value(self, context: Scope) -> Any:
        """
        Evaluates the expression.

        :param context: The scope in which the template runs.
        :return: The value of a single term, or a list with the result of
            the operators.
        """
        return self.root.value(context)

    # Any: the items of the value.
    def values(self, context: Scope) -> list[Any]:
        """
        Evaluates the expression, and returns its value as a list, see
        as_list().

        :param context: The scope in which the template runs.
        """
        return as_list(self.value(context), self.root)

    def is_true(self, context: Scope) -> bool:
        """
        Evaluates the expression as a condition, which is true if the first
        item of the value is true. An empty list is false.

        :param context: The scope in which the template runs.
        """
        values = self.values(context)
        return len(values) > 0 and bool(values[0])

    def dump(self, indent: int = 0) -> None:
        """
        Prints the expression tree to stdout.

        :param indent: The indentation of this token.
        """
        print((' ' * indent) + self.name, 'start')
        self.root.dump(indent + 1)
        print((' ' * indent) + self.name, 'end')
