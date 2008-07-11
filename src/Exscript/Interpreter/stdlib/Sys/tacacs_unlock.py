def execute(scope, user = [None], password = [None]):
    wq   = scope.get('__exscript__').workqueue
    user = scope.get('__user__')
    lock = wq.get_data('lock::authentication::tacacs::%s' % user)
    lock.release()
    return 1
