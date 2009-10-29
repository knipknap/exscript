from termconnect.Exception import InvalidCommandException

True  = 1
False = 0

def execute(scope, password = [None]):
    scope.get('__connection__').auto_authorize(password = password[0])
    return True
