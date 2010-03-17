class Task(object):
    def __init__(self, actions, tasks):
        self.actions = actions
        self.tasks   = tasks
        #print self.__class__.__name__, actions, tasks

    def call(self, conn):
        print "Task called."
        for action in self.actions:
            name = action[0]
            if name in ('sendline', 'execline', 'set-prompt'):
                print name, action[1:]
                #FIXME
            elif name == 'invoke-task':
                self.tasks[action[1]].call(conn, *action[2])
            elif name == 'invoke-script':
                print name, action[1:]
                #FIXME
            else:
                raise Exception('BUG: invalid action %s' % name)
