def execute(scope, password = [None]):
    conn = scope.get('_connection')
    conn.authorize(password[0], wait = 1)
    return 1
