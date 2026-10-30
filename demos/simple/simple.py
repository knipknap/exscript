#!/usr/bin/env python3
from Exscript.protocols import SSH2
from Exscript.util.interact import read_login

account = read_login()

conn = SSH2()
conn.connect('localhost')
conn.login(account)
conn.execute('ls -l')

# Fetch a clean response (no command echo, no NUL/BEL/BS, no ANSI codes).
print("Response was:", repr(conn.get_response()))

# Close the session gracefully (driver sends logout command like 'exit')
conn.close()
