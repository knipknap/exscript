def execute(scope, user = [None]):
    accm = scope.get('__exscript__').account_manager
    if user[0] is None:
        account = scope.get('__account__')
    else:
        account = accm.get_account_from_name(user[0])
    accm.acquire_account(account)
    return 1
