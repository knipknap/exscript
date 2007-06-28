from WorkQueue.Action import Action

True  = 1
False = 0

class Close(Action):
    def __init__(self):
        Action.__init__(self)


    def _on_data_received(self, data, args):
        self.emit('data_received', data)


    def execute(self, global_context, local_context):
        assert global_context is not None
        assert local_context  is not None
        local_context['transport'].set_on_data_received_cb(self._on_data_received)
        local_context['transport'].close()
        local_context['transport'].set_on_data_received_cb(None)
        return True
