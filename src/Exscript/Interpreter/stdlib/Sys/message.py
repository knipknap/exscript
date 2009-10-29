import sys

signature = [('self', 'string')]

def execute(scope, string):
    exscript = scope.get('__connection__').get_exscript()
    exscript._print(string[0] + '\n')
    return 1
