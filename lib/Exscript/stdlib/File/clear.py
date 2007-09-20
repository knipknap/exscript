signature = [('self', 'string')]

def execute(scope, filename):
    file = open(filename[0], 'w')
    file.close()
    return 1
