from Exscript.util.mail import Mail
from TkExscript         import MailWindow
mail = Mail(subject = 'Test me', body = 'hello world')
MailWindow(mail).mainloop()
