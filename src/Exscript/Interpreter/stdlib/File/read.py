signature = [('self', 'string')]

def execute(scope, filename):
    file  = open(filename[0], 'r')
    lines = file.readlines()
    file.close()
    scope.define(_buffer = lines)
    return lines
