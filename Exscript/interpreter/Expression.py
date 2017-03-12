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
from __future__ import print_function
from Exscript.parselib import Token
from Exscript.interpreter.ExpressionNode import ExpressionNode

class Expression(Token):
    def __init__(self, lexer, parser, parent):
        Token.__init__(self, 'Expression', lexer, parser, parent)

        # Parse the expression.
        self.root = ExpressionNode(lexer, parser, parent)

        # Reorder the tree according to the operator priorities.
        self.prioritize(self.root)
        self.mark_end()


    def prioritize(self, start, prio = 1):
        #print "Prioritizing from", start.op, "with prio", prio, (start.lft, start.rgt)
        if prio == 6:
            return
        root = start
        while root is not None and root.priority() <= prio:
            root = root.rgt
        if root is None:
            self.prioritize(start, prio + 1)
            return

        # Find the next node that has the current priority.
        previous = root
        current  = root.rgt
        while current is not None and current.priority() != prio:
            previous = current
            current  = current.rgt
        if current is None:
            self.prioritize(start, prio + 1)
            return

        # Reparent the expressions.
        #print "Prio of", root.op, 'is higher than', current.op
        previous.rgt = current.lft
        current.lft  = root

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

    def dump(self, indent = 0):
        print((' ' * indent) + self.name, 'start')
        self.root.dump(indent + 1)
        print((' ' * indent) + self.name, 'end.')
