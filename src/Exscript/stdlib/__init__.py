# Copyright (C) 2007 Samuel Abels, http://debain.org
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import connection
import crypt
import device
import file
import ipv4
import list
import string
import mysys

functions = {
    'connection.authenticate':   connection.authenticate,
    'connection.authorize':      connection.authorize,
    'connection.auto_authorize': connection.auto_authorize,
    'connection.close':          connection.close,
    'connection.exec':           connection.exec_,
    'connection.execline':       connection.execline,
    'connection.send':           connection.send,
    'connection.sendline':       connection.sendline,
    'connection.set_error':      connection.set_error,
    'connection.set_prompt':     connection.set_prompt,
    'connection.set_timeout':    connection.set_timeout,
    'connection.wait_for':       connection.wait_for,
    'crypt.otp':                 crypt.otp,
    'device.guess_os':           device.guess_os,
    'device.model':              device.model,
    'device.os':                 device.os,
    'device.vendor':             device.vendor,
    'file.chmod':                file.chmod,
    'file.clear':                file.clear,
    'file.exists':               file.exists,
    'file.mkdir':                file.mkdir,
    'file.read':                 file.read,
    'file.rm':                   file.rm,
    'file.write':                file.write,
    'ipv4.in_network':           ipv4.in_network,
    'ipv4.mask':                 ipv4.mask,
    'ipv4.mask2pfxlen':          ipv4.mask2pfxlen,
    'ipv4.pfxlen2mask':          ipv4.pfxlen2mask,
    'ipv4.pfxmask':              ipv4.pfxmask,
    'ipv4.remote_ip':            ipv4.remote_ip,
    'list.new':                  list.new,
    'list.unique':               list.unique,
    'string.replace':            string.replace,
    'sys.message':               mysys.message,
    'sys.tacacs_lock':           mysys.tacacs_lock,
    'sys.tacacs_unlock':         mysys.tacacs_unlock,
    'sys.run':                   mysys.run,
    'sys.wait':                  mysys.wait,
}
