class Task(object):
    def __init__(self, name, actions):
        self.name    = name
        self.actions = actions

    def call(self, conn, order):
        for action in self.actions:
            name = action[0]
            if name == 'connect':
                conn.open()
            elif name == 'autologin':
                conn.open()
                conn.authenticate(wait = True)
                conn.auto_authorize(wait = True)
            elif name == 'sendline':
                conn.send(action[1] + '\r')
            elif name == 'execline':
                conn.execute(action[1])
            elif name == 'expect':
                conn.expect(action[1])
            elif name == 'set-prompt':
                conn.set_prompt(action[1])
            elif name == 'invoke-task':
                action[1].call(conn, order, *action[2])
            elif name == 'invoke-python':
                action[1](conn, order)
            else:
                raise Exception('BUG: invalid action %s' % name)
