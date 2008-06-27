def execute(scope, data):
    conn     = scope.get('__connection__')
    response = []
    for line in data:
        conn.send(line)
        response += conn.expect_prompt()
    scope.define(_buffer = response)
    return 1
