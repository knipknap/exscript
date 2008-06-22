signature = [('self'), ('self', 'regex')]

def execute(scope, prompt = None):
    conn = scope.get('_connection')
    conn.set_prompt(prompt)
    return 1
