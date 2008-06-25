def execute(scope, data):
    conn     = scope.get('_connection')
    response = []
    for line in data:
        conn.execute(line)
        response += conn.response.split('\n')[1:]
    scope.define(_buffer = response)
    return 1
