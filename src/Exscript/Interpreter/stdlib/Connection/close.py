def execute(scope):
    conn = scope.get('__connection__')
    conn.close(True)
    scope.define(_buffer = conn.response)
    return 1
