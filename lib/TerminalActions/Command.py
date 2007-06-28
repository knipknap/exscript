from WorkQueue.Action import Action

True  = 1
False = 0

class Command(Action):
    def __init__(self, command):
        assert command is not None
        Action.__init__(self)
        self.command = command


    def _on_data_received(self, data, args):
        self.emit('data_received', data)


    def execute(self, global_context, local_context):
        assert global_context is not None
        assert local_context  is not None
        local_context['transport'].set_on_data_received_cb(self._on_data_received)
        local_context['transport'].execute(self.command)
        local_context['transport'].set_on_data_received_cb(None)
        return True
