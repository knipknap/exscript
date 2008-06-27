signature = [('self', 'regex')]

def execute(scope, prompt):
    conn = scope.get('__connection__')
    conn.expect(prompt)
    scope.define(_buffer = conn.response)
    return 1
