import sys

def write(scope, filename, lines):
    file = open(filename[0], 'a')
    file.writelines(['%s\n' % line.rstrip() for line in lines])
    file.close()
    return 1

def read(scope, filename):
    file  = open(filename[0], 'r')
    lines = file.readlines()
    file.close()
    scope.define(_buffer = lines)
    return lines

def clear(scope, filename):
    file = open(filename[0], 'w')
    file.close()
    return 1
