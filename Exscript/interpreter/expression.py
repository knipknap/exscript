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
from __future__ import print_function, absolute_import, division
from builtins import str
import Exscript.interpreter.term
from ..parselib import Token


class ExpressionNode(Token):

    def __init__(self, lexer, parser, parent, parent_node=None):
        # Skip whitespace before initializing the token to make sure that self.start
        # points to the beginning of the expression (which makes for prettier error
        # messages).
        lexer.skip(['whitespace', 'newline'])

        Token.__init__(self, 'ExpressionNode', lexer, parser, parent)
        self.lft = None
        self.rgt = None
        self.op = None
        self.op_type = None
        self.parent_node = parent_node

        # The "not" operator requires special treatment because it is
        # positioned left of the term.
        if not lexer.current_is('logical_operator', 'not'):
            self.lft = Exscript.interpreter.term.Term(lexer, parser, parent)

            # The expression may end already (a single term is also an
            # expression).
            lexer.skip(['whitespace', 'newline'])
            if not lexer.current_is('arithmetic_operator') and \
               not lexer.current_is('logical_operator') and \
               not lexer.current_is('comparison') and \
               not lexer.current_is('regex_delimiter'):
                self.mark_end()
                return

        # Expect the operator.
        self.op_type, self.op = lexer.token()
        if not lexer.next_if('arithmetic_operator') and \
           not lexer.next_if('logical_operator') and \
           not lexer.next_if('comparison') and \
           not lexer.next_if('regex_delimiter'):
            self.mark_end()
            msg = 'Expected operator but got %s' % self.op_type
            lexer.syntax_error(msg, self)

        # Expect the second term.
        self.rgt = ExpressionNode(lexer, parser, parent, self)
        self.mark_end()

    def priority(self):
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
            raise Exception('Invalid operator.')

    def value(self, context):
        # Special behavior where we only have one term.
        if self.op is None:
            return self.lft.value(context)
        elif self.op == 'not':
            return [not self.rgt.value(context)[0]]

        # There are only two types of values: Regular expressions and lists.
        # We also have to make sure that empty lists do not cause an error.
        lft_lst = self.lft.value(context)
        if type(lft_lst) == type([]):
            if len(lft_lst) > 0:
                lft = lft_lst[0]
            else:
                lft = ''
        rgt_lst = self.rgt.value(context)
        if type(rgt_lst) == type([]):
            if len(rgt_lst) > 0:
                rgt = rgt_lst[0]
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

    def dump(self, indent=0):
        print((' ' * indent) + self.name, self.op, 'start')
        if self.lft is not None:
            self.lft.dump(indent + 1)
        print((' ' * (indent + 1)) + 'Operator', self.op)
        if self.rgt is not None:
            self.rgt.dump(indent + 1)
        print((' ' * indent) + self.name, self.op, 'end.')


class Expression(Token):

    def __init__(self, lexer, parser, parent):
        Token.__init__(self, 'Expression', lexer, parser, parent)

        # Parse the expression.
        self.root = ExpressionNode(lexer, parser, parent)

        # Reorder the tree according to the operator priorities.
        self.prioritize(self.root)
        self.mark_end()

    def prioritize(self, start, prio=1):
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

    def value(self, context):
        return self.root.value(context)

    def dump(self, indent=0):
        print((' ' * indent) + self.name, 'start')
        self.root.dump(indent + 1)
        print((' ' * indent) + self.name, 'end.')
