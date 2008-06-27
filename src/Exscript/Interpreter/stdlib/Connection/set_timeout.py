signature = [('self', 'integer')]

def execute(scope, timeout):
    conn = scope.get('__connection__')
    conn.set_timeout(int(timeout[0]))
    return 1
