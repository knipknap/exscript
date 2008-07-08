import os.path, time

def execute(scope, host, filename):
    user          = scope.get('__user__')
    password      = scope.get('__password__')
    exscript      = scope.get('__exscript__')
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

    exscript.define_host(hostname, **vars)
    job = exscript._new_job(hostname,
                            user     = user,
                            password = password,
                            filename = filename,
                            priority = 'force')
    while exscript.workqueue.in_queue(job):
        time.sleep(1)
        continue
    return 1
