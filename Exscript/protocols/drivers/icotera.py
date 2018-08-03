"""
A driver for Icotera CPE
"""
import re
from Exscript.protocols.drivers import Driver


class IcoteraDriver(Driver):

    def __init__(self):
        """
        Constructor of the IcoteraDriver.
        """
        Driver.__init__(self, 'icotera')
        self.user_re = [re.compile(r'user ?name: ?$', re.I)]
        self.password_re = [re.compile(r'(?:[\r\n]Password: ?|last resort password:)$')]
        self.prompt_re = [re.compile(r'.*?>\s*$')]
        self.error_re = [re.compile(r'ERROR')]

    def check_head_for_os(self, string):
        if 'ICOTERA' in string:
            return 80
        return 0