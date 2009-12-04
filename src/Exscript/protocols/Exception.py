class NetworkException(Exception):
    pass

class TransportException(Exception):
    pass

class LoginFailure(Exception):
    pass

class InvalidCommandException(TransportException):
    pass
