#import copy
from Action import Action

True  = 1
False = 0

class CommandScript(Action):
    def __init__(self, exscript, *args, **kwargs):
        assert exscript is not None
        Action.__init__(self)
        self.exscript = exscript
        #FIXME: In Python > 2.2 you should be able to do this:
        #self.exscript = copy.deepcopy(exscript)
        self.exscript.signal_connect('notify', self.emit)


    def _on_data_received(self, data, args):
        self.emit('data_received', data)


    def execute(self, global_context, local_context):
        assert global_context is not None
        assert local_context  is not None
        local_context['transport'].set_on_data_received_cb(self._on_data_received)
        conn = local_context['transport']
        self.exscript.define(_connection = conn)
        self.exscript.execute()
        local_context['transport'].set_on_data_received_cb(None)
        return True
