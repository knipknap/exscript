from external.SpiffSignal import Trackable

class Task(Trackable):
    """
    Represents a batch of running actions.
    """
    def __init__(self, queue):
        Trackable.__init__(self)
        self.queue     = queue
        self.actions   = []
        self.completed = 0

    def _on_action_done(self, action):
        self.completed += 1
        if self.is_completed():
            self.signal_emit('done')

    def is_completed(self):
        return self.completed == len(self.actions)

    def wait(self):
        """
        Waits until all actions in the task have completed.
        """
        for action in self.actions:
            self.queue.wait_for(action)

    def add_action(self, action):
        """
        Adds a new action to the task.

        @type  action: Action
        @param action: The action to be added.
        """
        self.actions.append(action)
        action.signal_connect('aborted',   self._on_action_done)
        action.signal_connect('succeeded', self._on_action_done)
