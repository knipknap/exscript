def execute(scope, data, wait = None):
    conn = scope.get('__connection__')
    for line in data:
        conn.send(line)
    return 1
