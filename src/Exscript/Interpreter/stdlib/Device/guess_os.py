import re
import util

def execute(scope):
    conn = scope.get('_connection')
    return [conn.guess_os()]
