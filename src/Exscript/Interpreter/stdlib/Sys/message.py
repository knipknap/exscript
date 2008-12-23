import sys

signature = [('self', 'string')]

def execute(scope, string):
    exscript = scope.get('__exscript__')
    exscript._print(string[0] + '\n')
    return 1
