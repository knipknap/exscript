import re

def set_prompt(scope, prompt = None):
    conn = scope.get('_connection')
    conn.set_prompt(prompt)
    return 1


def set_timeout(scope, timeout):
    conn = scope.get('_connection')
    conn.set_timeout(timeout)
    return 1


def send(scope, data):
    conn = scope.get('_connection')
    for line in data:
        conn.send(line)
    scope.define(_buffer = conn.expect_prompt())
    return 1
