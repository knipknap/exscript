signature = [('self'), ('self', 'regex')]

def execute(scope, prompt = None):
    conn = scope.get('__connection__')
    conn.set_prompt(prompt)
    return 1
