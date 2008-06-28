def execute(scope, password = [None]):
    conn = scope.get('__connection__')
    wq   = scope.get('__workqueue__')
    user = scope.get('__user__')
    lock = wq.get_data('lock::authentication::tacacs::%s' % user)

    # Send the authorization command.
    lock.acquire()
    try:
        if conn.guess_os() in ('ios', 'ios-xr'):
            conn.send('enable\r')
        elif conn.guess_os() == 'junos':
            lock.release()
            return # does not require authorization
        else:
            lock.release()
            return # skip unsupported OSes
    except:
        lock.release()
        return

    # Send the login information.
    conn.authorize(password[0], wait = 1)
    lock.release()
    return 1
