"""
A driver for Ciena SAOS carrier ethernet devices
"""
import re
from Exscript.protocols.drivers.driver import Driver

_user_re = [re.compile(r'[^:]* login: ?$', re.I)]
_password_re = [re.compile(r'Password: ?$')]
_prompt_re = [re.compile(r'[\r\n][\-\w+\.:/]+[>#] ?$')]
_error_re = [re.compile(r'SHELL PARSER FAILURE'),
             re.compile(r'invalid input', re.I),
             re.compile(r'(?:incomplete|ambiguous) command', re.I),
             re.compile(r'connection timed out', re.I),
             re.compile(r'[^\r\n]+ not found', re.I)]


class CienaSAOSDriver(Driver):

    def __init__(self):
        Driver.__init__(self, 'cienasaos')
        self.user_re = _user_re
        self.password_re = _password_re
        self.prompt_re = _prompt_re
        self.error_re = _error_re

    def check_head_for_os(self, string):
        if 'SAOS is True Carrier Ethernet TM software' in string:
            return 90
        return 0

    def init_terminal(self, conn):
        conn.execute('system shell session set more off')
