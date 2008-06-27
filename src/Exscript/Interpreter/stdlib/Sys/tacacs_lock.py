def execute(scope, user = [None], password = [None]):
    wq   = scope.get('__workqueue__')
    user = scope.get('__user__')
    lock = wq.get_data('lock::authentication::tacacs::%s' % user)
    lock.acquire()
    return 1
