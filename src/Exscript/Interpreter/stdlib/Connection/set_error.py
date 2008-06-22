def execute(scope, error_re = None):
    conn = scope.get('_connection')
    conn.set_error(error_re)
    return 1
