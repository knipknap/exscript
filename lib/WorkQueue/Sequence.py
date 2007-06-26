import threading
from Action import Action

True  = 1
False = 0

class Sequence(Action):
    def __init__(self, *args, **kwargs):
        Action.__init__(self)
        lock_key_prefix             = 'lock::filesystem::'
        self.actions                = []
        self.logfile                = kwargs.get('logfile', None)
        self.logfile_lock_key       = None
        self.error_logfile          = kwargs.get('error_logfile', None)
        self.error_logfile_lock_key = None
        self.global_context         = None
        if self.logfile is not None:
            self.logfile_lock_key = lock_key_prefix + self.logfile
        if self.error_logfile is not None:
            self.error_logfile_lock_key = lock_key_prefix + self.error_logfile
        if kwargs.has_key('actions'):
            assert type(kwargs['actions']) == type([])
            for action in kwargs['actions']:
                self.add(action)


    def _log(self, logfile, lock_key, data):
        if logfile is None or lock_key is None:
            return
        logfile_lock = self.global_context.get(lock_key, None)
        if logfile_lock is None:
            logfile_lock = threading.Lock()
            self.global_context[lock_key] = logfile_lock
        logfile_lock.acquire()
        logfile = open(logfile, 'a')
        logfile.write(data)
        logfile_lock.release()


    def _on_log_data_received(self, name, data):
        if name == 'notify':
            self._log(self.logfile, self.logfile_lock_key, 'NOTIFICATION: %s' % data)
        else:
            self._log(self.logfile, self.logfile_lock_key, data)
        self.emit(name, data)


    def add(self, action):
        action.signal_connect('data_received', self._on_log_data_received)
        action.signal_connect('notify',        self._on_log_data_received)
        self.actions.append(action)


    def execute(self, global_context, local_context):
        assert local_context  is not None
        assert global_context is not None
        self.global_context = global_context
        try:
            for action in self.actions:
                action.debug = self.debug
                if not action.execute(global_context, local_context):
                    return False
        except Exception, e:
            self._log(self.error_logfile, self.error_logfile_lock_key, '%s' % e)
            raise
        return True
