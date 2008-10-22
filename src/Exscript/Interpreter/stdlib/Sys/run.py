import os.path, time

def execute(scope, host, filename):
    user          = scope.get('__user__')
    password      = scope.get('__password__')
    exscript      = scope.get('__exscript__')
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

    runner.define_host(hostname, **vars)
    sequence = runner._get_sequence(hostname,
                                    user     = user,
                                    password = password,
                                    filename = filename,
                                    priority = 'force')
    exscript.workqueue.enqueue(sequence)
    while exscript.workqueue.in_queue(sequence):
        time.sleep(1)
        continue
    return 1
