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
The decorator that marks functions of the template language as secure.
"""

from collections.abc import Callable
from functools import wraps
from typing import Any, cast


def secure_function[**P, R](function: Callable[P, R]) -> Callable[P, R]:
    """Decorator to indicate a secure function in scripts.

    The function is secure, if it does not have any side effects on and does not
    read data from the system where the interpreter is running.

    The decorator returns a wrapper that calls the function and has the
    attribute ``_is_secure``. A template that is compiled in secure mode
    may only call functions that have this attribute.

    :param function: The function that is marked as secure.
    :return: The wrapper, with the name, docstring and signature of the
        function.
    """

    @wraps(function)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return function(*args, **kwargs)

    # The type of the wrapper (functools._Wrapped) does not declare the attribute.
    cast(Any, wrapper)._is_secure = True
    return wrapper
