signature = [('self', 'list')]

def execute(scope, data):
    conn = scope.get('_connection')
    for line in data:
        conn.send(line)
    scope.define(_buffer = conn.expect_prompt())
    return 1
