def execute(scope, filename, lines):
    file = open(filename[0], 'a')
    file.writelines(['%s\n' % line.rstrip() for line in lines])
    file.close()
    return 1
