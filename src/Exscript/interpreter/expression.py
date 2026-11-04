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

from typing import TYPE_CHECKING, Any, cast

import Exscript.interpreter.term

from ..parselib import Lexer, Token
from .scope import Scope

if TYPE_CHECKING:
    from .parser import Parser


class ExpressionNode(Token):
    """
    A node of an expression: a term, optionally followed by an operator and
    the rest of the expression, which is the right-hand node. An expression
    that starts with "not" has no term.
    """

    def __init__(
        self,
        lexer: Lexer,
        parser: 'Parser',
        parent: Scope,
        parent_node: 'ExpressionNode | None' = None,
    ) -> None:
        """
        Constructor. Parses a term and, if an operator follows, the operator
        and the rest of the expression.

        :param lexer: The lexer that reads the template.
        :param parser: The parser of the template.
        :param parent: The scope that contains the expression.
        :param parent_node: The node whose right-hand node this node is, or
            None.
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
        self.parent_node = parent_node

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

        # Expect the second term.
        self.rgt = ExpressionNode(lexer, parser, parent, self)
        # End of statement.
        self.mark_end(rstrip=True)

    def priority(self) -> int:
        """
        Returns the priority of the operator of the node, from 1 for "and"
        and "or" to 7 for "%", or 8 if the node has no operator. Raises an
        Exception for an unknown operator.
        """
        if self.op is None:
            return 8
        elif self.op_type == 'arithmetic_operator' and self.op == '%':
            return 7
        elif self.op_type == 'arithmetic_operator' and self.op == '*':
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
        Evaluates the node. A list operand stands for its first item, or ''
        if it is empty. Arithmetic operators raise an ExecuteError if an
        operand is not a number.

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
            return [not cast(Token, self.rgt).value(context)[0]]

        # There are only two types of values: Regular expressions and lists.
        # We also have to make sure that empty lists do not cause an error.
        # The first item of a list can be a string, a number or anything else
        # that a function returned, hence Any.
        lft_lst = cast(Token, self.lft).value(context)
        if type(lft_lst) == type([]):
            if len(lft_lst) > 0:
                lft: Any = lft_lst[0]
            else:
                lft = ''
        rgt_lst = cast(Token, self.rgt).value(context)
        if type(rgt_lst) == type([]):
            if len(rgt_lst) > 0:
                rgt: Any = rgt_lst[0]
            else:
                rgt = ''

        if self.op_type == 'arithmetic_operator' and self.op != '.':
            error = 'Operand for %s is not a number' % (self.op)
            try:
                lft = int(lft)
            except ValueError:
                self.lexer.runtime_error(error, self.lft)
            try:
                rgt = int(rgt)
            except ValueError:
                self.lexer.runtime_error(error, self.rgt)

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
        Constructor. Parses the expression and reorders its nodes by the
        priority of the operators.

        :param lexer: The lexer that reads the template.
        :param parser: The parser of the template.
        :param parent: The scope that contains the expression.
        """
        Token.__init__(self, self.__class__.__name__, lexer, parser, parent)

        # Parse the expression.
        self.root = ExpressionNode(lexer, parser, parent)

        # Reorder the tree according to the operator priorities.
        self.prioritize(self.root)

        # End of statement.
        self.mark_end(rstrip=True)

    # start is an ExpressionNode, a Term or None. It is Any because the code
    # walks Terms like nodes (a Term has lft, rgt and op set to None, and the
    # priority 6) and relies on Terms never reaching the reparenting part,
    # which needs attributes that only nodes have.
    def prioritize(self, start: Any, prio: int = 1) -> None:
        """
        Reorders the tree from the given node on, so that operators with a
        higher priority are evaluated first: the first node with the given
        priority becomes the parent of the preceding nodes with a higher
        priority. Continues recursively with the priorities up to 5.

        :param start: The node at which the reordering starts.
        :param prio: The priority of the operators to move up.
        """
        # print("Prioritizing from", start.op, "with prio", prio, (start.lft,)
        # start.rgt)
        if prio == 6:
            return

        # Search the tree for the first node that has at least the
        # given prio.
        root = start
        while root is not None and root.priority() <= prio:
            root = root.rgt

        # If no such node exists, search for weaker priorities.
        if root is None:
            self.prioritize(start, prio + 1)
            return

        # Check if there is any child node that has a better priority.
        previous = root
        current = root.rgt
        while current is not None and current.priority() != prio:
            previous = current
            current = current.rgt

        # If none was found, continue with sorting weaker priorities.
        if current is None:
            self.prioritize(start, prio + 1)
            return

        # So we found a node that has a better prio than it's parent.
        # Reparent the expressions.
        # print("Prio of", root.op, 'is higher than', current.op)
        previous.rgt = current.lft
        current.lft = root

        # Change the pointer of the parent of the root node.
        # If this was the root of the entire tree we need to change that as
        # well.
        if root.parent_node is None:
            self.root = current
        elif root.parent_node.lft == root:
            root.parent_node.lft = current
        elif root.parent_node.rgt == root:
            root.parent_node.rgt = current

        root.parent_node = current

        # Go ahead prioritizing the children.
        self.prioritize(current.lft, prio + 1)
        self.prioritize(current.rgt, prio)

    # Any: see ExpressionNode.value().
    def value(self, context: Scope) -> Any:
        """
        Evaluates the expression.

        :param context: The scope in which the template runs.
        :return: The value of a single term, or a list with the result of
            the operators.
        """
        return self.root.value(context)

    def dump(self, indent: int = 0) -> None:
        """
        Prints the expression tree to stdout.

        :param indent: The indentation of this token.
        """
        print((' ' * indent) + self.name, 'start')
        self.root.dump(indent + 1)
        print((' ' * indent) + self.name, 'end')
