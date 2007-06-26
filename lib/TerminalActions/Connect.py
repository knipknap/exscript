import threading
from Action import Action

True  = 1
False = 0

class Connect(Action):
    def __init__(self, transport_module, hostname, *args, **kwargs):
        assert transport_module is not None
        assert hostname         is not None
        Action.__init__(self)
        self.hostname = hostname
        kwargs['debug']            = self.debug
        kwargs['on_data_received'] = self._on_data_received
        self.transport             = transport_module.Transport(**kwargs)


    def _on_data_received(self, data, args):
        self.emit('data_received', data)


    def execute(self, global_context, local_context):
        assert global_context is not None
        assert local_context  is not None
        self.transport.debug = self.debug
        self.global_context  = global_context
        if not self.transport.connect(self.hostname):
            raise Exception, 'Connect failed: %s' % self.transport.error()
        local_context['hostname']  = self.hostname
        local_context['transport'] = self.transport
        local_context['transport'].set_on_data_received_cb(None)
        return True
