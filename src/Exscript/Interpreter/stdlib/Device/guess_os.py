import re
import util

def execute(scope):
    conn = scope.get('__connection__')
    return [conn.guess_os()]
