def execute(scope, data):
    conn = scope.get('_connection')
    for line in data:
        conn.send(line + '\r')
    return 1
