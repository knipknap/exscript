"""
Driver for Extreme XOS devices.
"""
import re
from Exscript.protocols.drivers.driver import Driver

_user_re      = [re.compile(r'[\n]login: $')]
_password_re  = [re.compile(r'[\r]password: $')]
_prompt_re    = [re.compile(r'[\r\n][a-zA-Z0-9-_ .]+# $')]
_extremexos_re = re.compile(r'\r\n\r\r\n\rExtremeXOS\r\nCopyright', re.I)


class ExtremeDriver(Driver):
    def __init__(self):
        Driver.__init__(self, 'extremexos')
        self.user_re     = _user_re
        self.password_re = _password_re
        self.prompt_re   = _prompt_re

    def check_head_for_os(self, string):
        if _extremexos_re.search(string):
            return 80
        return 0
    def init_terminal(self,conn):
	conn.execute('disable clipaging\r')
