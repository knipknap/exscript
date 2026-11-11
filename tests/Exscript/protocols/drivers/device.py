"""
A virtual device with the prompts of a real one, for the tests of the drivers.
"""

import os

from Exscript import Account
from Exscript.emulators import VirtualDevice
from Exscript.protocols import Dummy

BANNER_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'banners')

# The authorization password differs from the login password.
ACCOUNT = Account('admin', 'login-secret', 'enable-secret', needs_lock=False)


def banner(name):
    """Returns the banner of the corpus with the given name (tests/Exscript/protocols/banners)."""
    with open(os.path.join(BANNER_DIR, name), encoding='utf-8', newline='') as fp:
        return fp.read()


def search(patterns, text):
    """Returns whether one of the given patterns matches the text."""
    return any(pattern.search(text) for pattern in patterns)


class Device(VirtualDevice):
    """
    Shows the banner, the login prompts if given, and the prompt; answers the
    commands that were added with add_command(), and others with the prompt
    only; and records the commands without their line breaks. With an
    enabled prompt, the enable command asks for a password, unless the
    password prompt is None, and the device shows the enabled prompt
    afterwards.

    :param login: The user name prompt and the password prompt of the login.
    """

    def __init__(
        self,
        prompt,
        banner='\r\n',
        login=None,
        enabled_prompt=None,
        enable_command='enable',
        enable_password_prompt='Password: ',
    ):
        login_type = VirtualDevice.LOGIN_TYPE_BOTH if login else VirtualDevice.LOGIN_TYPE_NONE
        super().__init__('r1', login_type=login_type, strict=False, banner=banner)
        if login:
            self.user_prompt, self.password_prompt = login
        self.prompt = prompt
        self.enabled_prompt = enabled_prompt
        self.enable_command = enable_command
        self.enable_password_prompt = enable_password_prompt
        self.received = []
        self._enabling = False

    def do(self, command):
        command = command.strip('\r\n')
        self.received.append(command)
        if self._enabling:  # the password, which is not echoed
            self._enabling = False
            self.prompt = self.enabled_prompt
            return '\r\n' + self.prompt
        if command == self.enable_command and self.enabled_prompt is not None:
            if self.enable_password_prompt is None:
                self.prompt = self.enabled_prompt
                return command + '\r\n' + self.prompt
            self._enabling = True
            return command + '\r\n' + self.enable_password_prompt
        return super().do(command)


def connect(test, device, driver, login=None, prompt=True):
    """
    Returns a Dummy connection with the given driver to the device, after the
    login with the given account, or else after the banner and the first
    prompt unless prompt is False.
    """
    conn = Dummy(device=device, driver=driver, timeout=1)
    conn.connect(device.hostname)
    test.addCleanup(conn.close, force=True)
    if login:
        conn.login(login)
    elif prompt:
        conn.expect_prompt()
    return conn
