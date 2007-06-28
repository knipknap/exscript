from AbstractMethod import AbstractMethod

class Transport:
    def __init__(self, *args, **kwargs):
        self.on_data_received_cb   = kwargs.get('on_data_received',      None)
        self.on_data_received_args = kwargs.get('on_data_received_args', None)


    def set_on_data_received_cb(self, func, args = None):
        self.on_data_received_cb   = func
        self.on_data_received_args = args


    def set_prompt(self, prompt = None):
        AbstractMethod()


    def set_timeout(self, timeout):
        AbstractMethod()


    def connect(self, hostname):
        AbstractMethod()


    def authenticate(self, user, password):
        AbstractMethod()


    def authorize(self, password):
        AbstractMethod()


    def expect_prompt(self):
        AbstractMethod()


    def execute(self, command):
        AbstractMethod()


    def send(self, data):
        AbstractMethod()


    def close(self):
        AbstractMethod()
