from Exscript.util.interact import read_login
from Exscript.protocols import SSH2

account = read_login()

conn = SSH2()
conn.connect('localhost')
conn.login(account)
conn.execute('ls -l')

print "Response was:", repr(conn.response)

conn.send('exit\r')
conn.close()
