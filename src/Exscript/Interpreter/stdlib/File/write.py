def execute(scope, filename, lines, mode = ['a']):
    file = open(filename[0], mode[0])
    file.writelines(['%s\n' % line.rstrip() for line in lines])
    file.close()
    return 1
