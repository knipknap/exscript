"""
A driver for the Adtran DSLAMs.

The DSLAMs only report "OpenSSH" in their SSH remote protocol id and have
no SSH banner so no possibility for check_*_for_os().

"""
from __future__ import absolute_import
from .driver import Driver


class AdtranDriver(Driver):

    def __init__(self):
        Driver.__init__(self, 'adtran')

    def init_terminal(self, conn):
        conn.execute('terminal length 0')
        conn.execute('terminal column 0')

    def auto_authorize(self, conn, account, flush, bailout):
        self.init_terminal(conn)
        conn.send('enable\r\n')
        conn.app_authorize(account, flush, bailout)
