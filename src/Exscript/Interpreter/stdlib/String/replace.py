def execute(scope, strings, source, dest):
    return [s.replace(source[0], dest[0]) for s in strings]
