import getpass

def get_login():
    """
    Returns a tuple containing the username and the password.
    May throw an exception if EOF is given by the user.
    """
    # Read username and password.
    try:
        env_user = getpass.getuser()
        user     = raw_input('Please enter your user name [%s]: ' % env_user)
        if user == '':
            user = env_user
    except:
        user = raw_input('Please enter your user name: ' % user)
    password = getpass.getpass('Please enter your password: ')
    return (user, password)
