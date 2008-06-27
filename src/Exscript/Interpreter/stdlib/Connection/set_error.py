def execute(scope, error_re = None):
    conn = scope.get('__connection__')
    conn.set_error(error_re)
    return 1
