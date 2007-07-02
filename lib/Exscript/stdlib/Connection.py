import re

def set_prompt(scope, prompt = None):
    conn = scope.get('_connection')
    conn.set_prompt(prompt)
    return 1


def set_timeout(scope, timeout):
    conn = scope.get('_connection')
    conn.set_timeout(timeout)
    return 1
