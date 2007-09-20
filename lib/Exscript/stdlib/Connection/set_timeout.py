signature = [('self', 'integer')]

def execute(scope, timeout):
    conn = scope.get('_connection')
    conn.set_timeout(timeout[0])
    return 1
