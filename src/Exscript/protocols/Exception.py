class TransportException(Exception):
    """
    Default exception that is thrown on most transport related errors.
    """
    pass

class LoginFailure(TransportException):
    """
    An exception that is thrown if the response of a connected host looked
    like it was trying to signal a login error during the authentication
    procedure.
    """
    pass

class InvalidCommandException(TransportException):
    """
    An exception that is thrown if the response of a connected host contained
    a string that looked like an error.
    """
    pass
