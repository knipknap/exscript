def execute(scope, password = [None]):
    conn = scope.get('__connection__')
    conn.transport.authorize(password[0], wait = 1)
    return 1
