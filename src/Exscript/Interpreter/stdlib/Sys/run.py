import os.path, time
from Exscript import Host

def execute(scope, host, filename):
    exscript      = scope.get('__connection__').get_exscript()
    runner        = scope.get('__runner__')
    exscript_file = scope.get('__filename__') or ''
    exscript_dir  = os.path.dirname(exscript_file)
    filename      = os.path.join(exscript_dir, filename[0])
    hostname      = host[0]

    vars = {}
    for key, value in scope.get_vars().iteritems():
        if key == 'hostname':
            continue
        if key.startswith('_'):
            continue
        if type(value) == type(execute):
            continue
        vars[key] = value

    host = Host(hostname)
    for key, value_list in vars.iteritems():
        for value in value_list:
            host.append(key, value)
    runner.set_options(filename = filename)
    sequence = runner._get_sequence(exscript, host)
    exscript._priority_enqueue_action(sequence, 1)
    while not exscript._action_is_completed(sequence):
        time.sleep(1)
        continue
    return 1
