def execute(scope, password = [None]):
    conn = scope.get('__connection__')
    conn.authorize(password[0], wait = 1)
    return 1
