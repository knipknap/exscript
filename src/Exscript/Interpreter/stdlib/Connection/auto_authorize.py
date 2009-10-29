from termconnect.Exception import InvalidCommandException

True  = 1
False = 0

def execute(scope, password = [None]):
    conn = scope.get('__connection__')
    accm = scope.get('__exscript__').account_manager

    # Send the authorization command.
    account = accm.acquire_account()
    try:
        if conn.guess_os() == 'ios':
            conn.send('enable\r')
        elif conn.guess_os() == 'junos':
            account.release()
            return # does not require authorization
        else:
            account.release()
            return # skip unsupported OSes
    except:
        account.release()
        raise

    # Send the login information.
    try:
        conn.authorize(account, wait = True, lock = False)
    except InvalidCommandException:
        account.release()
        return
    except:
        account.release()
        raise

    account.release()
    return True
