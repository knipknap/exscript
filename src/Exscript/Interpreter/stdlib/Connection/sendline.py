def execute(scope, data):
    conn = scope.get('__connection__')
    for line in data:
        conn.send(line + '\r')
    return 1
