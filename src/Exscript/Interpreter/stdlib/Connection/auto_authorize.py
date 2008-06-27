def execute(scope, password = [None]):
    conn = scope.get('__connection__')
    wq   = scope.get('__workqueue__')
    user = scope.get('__user__')
    lock = wq.get_data('lock::authentication::tacacs::%s' % user)

    # Send the authorization command.
    lock.acquire()
    if conn.guess_os() in ('ios', 'ios-xr'):
        conn.execute('enable')
    elif conn.guess_os() == 'junos':
        lock.release()
        return # does not require authorization
    else:
        lock.release()
        return # skip unsupported OSes

    # Send the login information.
    conn.authorize(password[0], wait = 1)
    lock.release()
    response = conn.response.split('\n')[1:]
    scope.define(_buffer = response)
    return 1
