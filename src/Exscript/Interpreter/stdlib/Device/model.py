import re
import util

signature = [('self', 'integer')]

def execute(scope, force = None):
    conn = scope.get('_connection')
    if force is None:
        util.update_host_info(scope, 0)
    elif force[0] == 1:
        util.update_host_info(scope, 1)
    return [conn.remote_info['model']]
