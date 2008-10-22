def execute(scope, user = [None]):
    if user[0] is None:
        account = scope.get('__account__')
    else:
        accm    = scope.get('__exscript__').account_manager
        account = accm.get_account_from_name(user[0])
    account.release()
    return 1
