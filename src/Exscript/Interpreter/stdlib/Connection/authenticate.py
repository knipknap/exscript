def execute(scope, user = [None], password = [None]):
    conn = scope.get('_connection')
    conn.authenticate(user[0], password[0], wait = 1)
    return 1
