from WorkQueue.Action import Action

True  = 1
False = 0

class Authorize(Action):
    def __init__(self, password):
        assert password is not None
        Action.__init__(self)
        self.password        = password
        self.lock_key_prefix = 'lock::authentication::tacacs::'


    def _on_data_received(self, data, args):
        self.emit('data_received', data)


    def tacacs_lock(self, context, user):
        key = self.lock_key_prefix + user
        if not context.has_key(key):
            context[key] = threading.Lock()
        return context[key]


    def execute(self, global_context, local_context):
        assert global_context is not None
        assert local_context  is not None
        local_context['transport'].set_on_data_received_cb(self._on_data_received)
        self.tacacs_lock(global_context, local_context['user']).acquire()
        local_context['transport'].authorize(self.password)
        self.tacacs_lock(global_context, local_context['user']).release()
        local_context['transport'].set_on_data_received_cb(None)
        return True
