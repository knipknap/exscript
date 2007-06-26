from Token import Token
from ExpressionNode import ExpressionNode

class Expression(Token):
    def __init__(self, parser, scope):
        Token.__init__(self, 'Expression', parser)

        # Parse the expression.
        self.root = ExpressionNode(parser, scope)

        # Reorder the tree according to the operator priorities.
        self.prioritize(self.root)


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
        if root.parent is None:
            self.root = current
        elif root.parent.lft == root:
            root.parent.lft = current
        elif root.parent.rgt == root:
            root.parent.rgt = current

        root.parent = current

        # Go ahead prioritizing the children.
        self.prioritize(current.lft, prio + 1)
        self.prioritize(current.rgt, prio)


    def value(self):
        return self.root.value()


    def dump(self, indent = 0):
        print (' ' * indent) + self.name, 'start'
        self.root.dump(indent + 1)
        print (' ' * indent) + self.name, 'end'
