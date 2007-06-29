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
from Token import Token
from Term  import Term
from Regex import Regex

class ExpressionNode(Token):
    def __init__(self, parser, scope, parent = None):
        # Skip whitespace before initializing the token to make sure that self.char
        # points to the beginning of the expression (which makes for prettier error
        # messages).
        while parser.next_if('whitespace') or parser.next_if('newline'):
            pass

        Token.__init__(self, 'ExpressionNode', parser)
        self.lft     = None
        self.rgt     = None
        self.op      = None
        self.op_type = None
        self.parent  = parent

        # The "not" operator requires special treatment because it is
        # positioned left of the term.
        if not parser.current_is('logical_operator', 'not'):
            self.lft = Term(parser, scope)

            # The expression may end already (a single term is also an
            # expression).
            while parser.next_if('whitespace') or parser.next_if('newline'):
                pass
            if not parser.current_is('arithmetic_operator') and \
               not parser.current_is('logical_operator') and \
               not parser.current_is('comparison'):
                return

        # Expect the operator.
        (self.op_type, self.op) = parser.token()
        if not parser.next_if('arithmetic_operator') and \
           not parser.next_if('logical_operator') and \
           not parser.next_if('comparison'):
            parser.syntax_error('Expected operator but got %s' % self.op_type)

        # Expect the second term.
        self.rgt = ExpressionNode(parser, scope, self)


    def priority(self):
        if self.op is None:
            return 5
        elif self.op == 'not':
            return 4
        elif self.op_type == 'arithmetic_operator':
            return 3
        elif self.op_type == 'comparison':
            return 2
        elif self.op_type == 'logical_operator':
            return 1


    def value(self):
        # Special behavior where we only have one term.
        if self.op is None:
            return self.lft.value()
        elif self.op == 'not':
            return not self.rgt.value()

        # There are three types of values: Integer, boolean, and lists.
        # We have to make sure that empty lists do not cause an error.
        lft = self.lft.value()
        if type(lft) == type([]) and len(lft) > 0:
            lft = lft[0]
        rgt = self.rgt.value()
        if type(rgt) == type([]) and len(rgt) > 0:
            rgt = rgt[0]

        # Two-term expressions.
        if self.op == 'is':
            #print "CMP:", lft, rgt
            return lft == rgt
        elif self.op == 'matches':
            regex   = self.rgt.value()
            subject = self.lft.value()[0]
            match   = None
            # The "matches" keyword requires a regular expression as the right hand
            # operand. The exception throws if "regex" does not have a match() method.
            try:
                match = regex.match(subject)
            except:
                error = 'Right hand operator is not a regular expression'
                self.parser.runtime_error(self.rgt, error)
            if match is None:
                return 0
            return 1
        elif self.op == 'is not':
            return lft != rgt
        elif self.op == 'ge':
            return int(lft) >= int(rgt)
        elif self.op == 'gt':
            return int(lft) > int(rgt)
        elif self.op == 'le':
            return int(lft) <= int(rgt)
        elif self.op == 'lt':
            return int(lft) < int(rgt)
        elif self.op == 'and':
            return lft and rgt
        elif self.op == 'or':
            return lft or rgt
        elif self.op == '*':
            return int(lft) * int(rgt)
        elif self.op == '/':
            return int(lft) / int(rgt)
        elif self.op == '+':
            return int(lft) + int(rgt)
        elif self.op == '-':
            return int(lft) - int(rgt)


    def dump(self, indent = 0):
        print (' ' * indent) + self.name, self.op, 'start'
        if self.lft is not None:
            self.lft.dump(indent + 1)
        print (' ' * (indent + 1)) + 'Operator', self.op
        if self.rgt is not None:
            self.rgt.dump(indent + 1)
        print (' ' * indent) + self.name, self.op, 'end'
