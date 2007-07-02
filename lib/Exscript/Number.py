class Number(object):
    def __init__(self, number):
        self.number = int(number)


    def value(self):
        return self.number


    def dump(self, indent = 0):
        print (' ' * indent) + 'Number', self.number
