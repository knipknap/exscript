signature = [('self', 'list', 'boolean')]

def execute(scope, data, wait = None):
    conn = scope.get('_connection')
    for line in data:
        conn.send(line)
    if wait is None or wait[0] == 1:
        scope.define(_buffer = conn.expect_prompt())
    return 1
