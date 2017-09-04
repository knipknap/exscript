#
# Copyright (C) 2010-2017 Samuel Abels
# The MIT License (MIT)
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
from Exscript.stdlib import connection
from Exscript.stdlib import crypt
from Exscript.stdlib import file
from Exscript.stdlib import ipv4
from Exscript.stdlib import list
from Exscript.stdlib import string
from Exscript.stdlib import mysys

functions = {
    'connection.authenticate':   connection.authenticate,
    'connection.authorize':      connection.authorize,
    'connection.auto_authorize': connection.auto_authorize,
    'connection.autoinit':       connection.autoinit,
    'connection.close':          connection.close,
    'connection.exec':           connection.exec_,
    'connection.execline':       connection.execline,
    'connection.guess_os':       connection.guess_os,
    'connection.send':           connection.send,
    'connection.sendline':       connection.sendline,
    'connection.set_error':      connection.set_error,
    'connection.set_prompt':     connection.set_prompt,
    'connection.set_timeout':    connection.set_timeout,
    'connection.wait_for':       connection.wait_for,
    'crypt.otp':                 crypt.otp,
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
    'ipv4.network':              ipv4.network,
    'ipv4.broadcast':            ipv4.broadcast,
    'ipv4.remote_ip':            ipv4.remote_ip,
    'list.new':                  list.new,
    'list.get':                  list.get,
    'list.length':               list.length,
    'list.unique':               list.unique,
    'string.replace':            string.replace,
    'string.tolower':            string.tolower,
    'string.toupper':            string.toupper,
    'sys.env':                   mysys.env,
    'sys.exec':                  mysys.execute,
    'sys.message':               mysys.message,
    'sys.wait':                  mysys.wait,
}
