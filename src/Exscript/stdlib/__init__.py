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
"""
The standard library of the template language: the functions that templates
call, such as ``connection.sendline()``, ``list.length()`` or ``sys.exec()``.

``functions`` maps the name that a template uses to the function. The
interpreter calls the function with the scope of the call, followed by the
values of the arguments. Template values are lists: a string argument, for
example, arrives as a list with one string. A regular expression, such as
``/[Ff]ailed/``, arrives compiled. Where the documentation of a function gives
the type of an argument or of the result, such as string, it means the type
of the items. The functions return a list, or True if they have no result.

Functions that run local commands or access local files are not secure (see
:func:`Exscript.stdlib.util.secure_function`): a template that is compiled
in secure mode cannot call them.
"""

from collections.abc import Callable
from typing import Any

from . import connection, crypt, file, ipv4, list, mysys, string

functions: dict[str, Callable[..., Any]] = {
    'connection.add_error': connection.add_error,
    'connection.add_prompt': connection.add_prompt,
    'connection.authenticate': connection.authenticate,
    'connection.authenticate_user': connection.authenticate_user,
    'connection.authorize': connection.authorize,
    'connection.auto_authorize': connection.auto_authorize,
    'connection.autoinit': connection.autoinit,
    'connection.close': connection.close,
    'connection.exec': connection.exec_,
    'connection.execline': connection.execline,
    'connection.expect': connection.expect,
    'connection.get_protocol': connection.get_protocol,
    'connection.guess_os': connection.guess_os,
    'connection.send': connection.send,
    'connection.sendline': connection.sendline,
    'connection.set_error': connection.set_error,
    'connection.set_prompt': connection.set_prompt,
    'connection.set_timeout': connection.set_timeout,
    'connection.wait_for': connection.wait_for,
    'crypt.otp': crypt.otp,
    'file.chmod': file.chmod,
    'file.clear': file.clear,
    'file.exists': file.exists,
    'file.mkdir': file.mkdir,
    'file.read': file.read,
    'file.rm': file.rm,
    'file.write': file.write,
    'ipv4.in_network': ipv4.in_network,
    'ipv4.mask': ipv4.mask,
    'ipv4.mask2pfxlen': ipv4.mask2pfxlen,
    'ipv4.pfxlen2mask': ipv4.pfxlen2mask,
    'ipv4.pfxmask': ipv4.pfxmask,
    'ipv4.network': ipv4.network,
    'ipv4.broadcast': ipv4.broadcast,
    'ipv4.remote_ip': ipv4.remote_ip,
    'list.new': list.new,
    'list.get': list.get,
    'list.length': list.length,
    'list.sort': list.sort,
    'list.reverse': list.reverse,
    'list.unique': list.unique,
    'string.replace': string.replace,
    'string.split': string.split,
    'string.strip': string.strip,
    'string.tolower': string.tolower,
    'string.toupper': string.toupper,
    'sys.env': mysys.env,
    'sys.exec': mysys.execute,
    'sys.message': mysys.message,
    'sys.wait': mysys.wait,
}
