from getpass    import getuser
from Exscript   import Account
from TkExscript import LoginWindow

def on_start(window):
    account = window.get_account()
    print("Username:",      account.get_name())
    print("Password:",      account.get_password())
    print("Authorization:", account.get_authorization_password())
    window.quit()

account = Account(getuser())
LoginWindow(account,
            show_authorization = True,
            on_start = on_start).mainloop()
