import __builtin__, sys, os
from Exscript.util.decorator import bind
from Service                 import Service

class PythonService(Service):
    def __init__(self,
                 daemon,
                 name,
                 filename,
                 cfg_dir,
                 queue     = None,
                 autoqueue = False):
        Service.__init__(self,
                         daemon,
                         name,
                         cfg_dir,
                         queue     = queue,
                         autoqueue = autoqueue)
        content             = open(filename).read()
        code                = compile(content, filename, 'exec')
        vars                = {}
        vars['__builtin__'] = __builtin__
        vars['__file__']    = filename
        vars['__service__'] = self

        # Load the module using evil path manipulation, but oh well...
        # can't think of a sane way to do this.
        sys.path.insert(0, os.path.dirname(filename))
        result = eval(code, vars)
        sys.path.pop(0)

        self.enter_func = vars.get('enter')
        self.run_func   = vars.get('run')

    def enter(self, order):
        if self.enter_func and not self.enter_func(self, order):
            return False
        self._autoqueue(order)
        return True

    def run(self, conn, order_id):
        hostname = conn.get_host().get_name()
        print "Running service", self.name, "on", hostname
        order = self.daemon.get_order_from_id(order_id)
        self.run_func(self, order, conn)
