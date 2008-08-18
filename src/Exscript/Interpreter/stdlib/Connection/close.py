def execute(scope):
    conn = scope.get('__connection__')
    conn.close(1)
    scope.define(_buffer = conn.response)
    return 1
