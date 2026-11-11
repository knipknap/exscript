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
OpenTelemetry instrumentation for Exscript. Requires the ``otel`` extra.

Usage::

    from Exscript.contrib.otel import ExscriptInstrumentor

    ExscriptInstrumentor().instrument()

Every call of ``connect()``, ``login()``, ``authenticate()``, ``send()``,
``execute()`` and ``close()`` on a protocol adapter creates a client span named
like ``SSH2 execute``, as a child of the current span. The duration of each call
is recorded in the histogram ``exscript.client.operation.duration``, in seconds.

Span attributes are ``server.address``, ``server.port``, ``exscript.protocol``
(the class name, e.g. ``SSH2``), ``exscript.operation``, ``exscript.os`` (the
guessed OS, once known), and ``error.type`` if the call raised. The histogram
has the attributes ``exscript.protocol``, ``exscript.operation`` and
``error.type``.

Commands and responses may contain secrets, so they are recorded only with
``instrument(capture_payload=True)``, as ``exscript.command`` and
``exscript.response``. They are truncated to ``max_payload_length`` characters
(default: 1024), and passwords sent by the login are recorded as ``<secret>``.

Further options of ``instrument()``:

- ``tracer_provider`` and ``meter_provider``, which default to the global ones;
- ``request_hook(span, conn)``, called before each call;
- ``response_hook(span, conn, result)``, called after each call that did not
  raise.
"""

from __future__ import annotations

import contextvars
import functools
import inspect
import time
from collections.abc import Callable, Collection
from typing import Any

from opentelemetry.instrumentation.instrumentor import (  # type: ignore[attr-defined]
    BaseInstrumentor,  # mypy cannot resolve it in this namespace package
)
from opentelemetry.metrics import Histogram, get_meter
from opentelemetry.trace import Span, SpanKind, Tracer, get_tracer

from Exscript.protocols import Protocol
from Exscript.version import __version__

RequestHook = Callable[[Span, Protocol], None]
ResponseHook = Callable[[Span, Protocol, Any], None]

_OPERATIONS = ('connect', 'login', 'authenticate', 'send', 'execute', 'close')
_APPLIED = '_exscript_otel_applied'
_DISABLED = '_exscript_otel_disabled'
# Calls take from milliseconds (send) to minutes (execute on a slow device).
_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120, 300)
# The call in progress in this context, as (id(conn), operation).
_active: contextvars.ContextVar[tuple[int, str] | None] = contextvars.ContextVar(
    'exscript_otel_active', default=None
)


def _protocol_classes() -> list[type[Protocol]]:
    """Returns Protocol and its subclasses, which may override instrumented methods."""
    classes, todo = [], [Protocol]
    while todo:
        cls = todo.pop()
        classes.append(cls)
        todo.extend(cls.__subclasses__())
    return classes


def _truncate(value: object, limit: int) -> str:
    """
    Returns the given value as a string, cut to the given number of
    characters and "..." if it is longer.
    """
    value = str(value)
    return value if len(value) <= limit else value[:limit] + '...'


def _set_connection_attributes(span: Span, conn: Protocol) -> None:
    """
    Sets the address and the port of the given connection on the span, if
    they are known, and the guessed OS, once it is known.
    """
    if conn.host:
        span.set_attribute('server.address', str(conn.host))
    if conn.port:
        span.set_attribute('server.port', int(conn.port))
    os_name = conn.guess_os()
    if os_name and os_name != 'unknown':
        span.set_attribute('exscript.os', os_name)


def _make_wrapper(
    original: Callable[..., Any],
    operation: str,
    tracer: Tracer,
    histogram: Histogram,
    options: dict[str, Any],
) -> Callable[..., Any]:
    """
    Returns a wrapper of the given method of the protocol adapters, which
    calls the method in a client span and records its duration in the
    histogram, as the module documentation describes. The wrapper calls the
    method without a span if the instrumentation is disabled for the
    adapter, if the same operation is in progress on the adapter (an
    override that calls super()), or if the arguments do not fit the method.

    :param original: The method, as the class defines it.
    :param operation: The name of the method, e.g. "execute".
    :param tracer: The tracer that creates the spans.
    :param histogram: The histogram of the durations.
    :param options: The options of instrument(): capture_payload,
        max_payload_length, request_hook and response_hook.
    """
    signature = inspect.signature(original)
    capture, limit = options['capture_payload'], options['max_payload_length']

    @functools.wraps(original)
    def wrapper(conn: Protocol, *args: Any, **kwargs: Any) -> Any:
        key = (id(conn), operation)
        if getattr(conn, _DISABLED, False) or _active.get() == key:
            return original(conn, *args, **kwargs)  # e.g. an override that calls super()
        try:
            arguments = signature.bind(conn, *args, **kwargs).arguments
        except TypeError:
            return original(conn, *args, **kwargs)  # raises the TypeError for the caller

        protocol = type(conn).__name__
        labels = {'exscript.protocol': protocol, 'exscript.operation': operation}
        attributes = dict(labels)
        if capture and operation == 'send':
            secret = getattr(conn, '_sending_secret', False)
            attributes['exscript.command'] = (
                '<secret>' if secret else _truncate(arguments['data'], limit)
            )
        elif capture and operation == 'execute':
            attributes['exscript.command'] = _truncate(arguments['command'], limit)

        with tracer.start_as_current_span(
            f'{protocol} {operation}', kind=SpanKind.CLIENT, attributes=attributes
        ) as span:
            if options['request_hook']:
                options['request_hook'](span, conn)
            token = _active.set(key)
            start = time.perf_counter()
            try:
                result = original(conn, *args, **kwargs)
            except BaseException as exc:
                labels['error.type'] = type(exc).__qualname__
                span.set_attribute('error.type', labels['error.type'])
                raise
            finally:
                _active.reset(token)
                histogram.record(time.perf_counter() - start, labels)
                _set_connection_attributes(span, conn)
            if capture and operation == 'execute':
                span.set_attribute('exscript.response', _truncate(conn.response, limit))
            if options['response_hook']:
                options['response_hook'](span, conn, result)
            return result

    setattr(wrapper, _APPLIED, True)
    return wrapper


class ExscriptInstrumentor(BaseInstrumentor):
    """Instruments all protocol adapters; see the module documentation."""

    def instrumentation_dependencies(self) -> Collection[str]:
        """
        Returns the packages that instrument() requires, unless its argument
        skip_dep_check is true: exscript, in any version.
        """
        return ('exscript',)

    def _instrument(self, **kwargs: Any) -> None:
        """
        Wraps the methods connect(), login(), authenticate(), send(),
        execute() and close() of Protocol and its subclasses, where a class
        defines them and they are not wrapped yet. instrument() calls it with
        its keyword arguments, the options in the module documentation.
        """
        tracer = get_tracer(__name__, __version__, kwargs.get('tracer_provider'))
        meter = get_meter(__name__, __version__, kwargs.get('meter_provider'))
        histogram = meter.create_histogram(
            'exscript.client.operation.duration',
            unit='s',
            description='Duration of Exscript protocol operations',
            explicit_bucket_boundaries_advisory=_BUCKETS,
        )
        options = {
            'capture_payload': kwargs.get('capture_payload', False),
            'max_payload_length': kwargs.get('max_payload_length', 1024),
            'request_hook': kwargs.get('request_hook'),
            'response_hook': kwargs.get('response_hook'),
        }
        for cls in _protocol_classes():
            for operation in _OPERATIONS:
                method = cls.__dict__.get(operation)
                if method is not None and not getattr(method, _APPLIED, False):
                    wrapper = _make_wrapper(method, operation, tracer, histogram, options)
                    setattr(cls, operation, wrapper)

    def _uninstrument(self, **kwargs: Any) -> None:
        """
        Restores the methods that _instrument() wrapped. uninstrument() calls
        it with its keyword arguments, which it ignores.
        """
        for cls in _protocol_classes():
            for operation in _OPERATIONS:
                # Any: getattr() below does not narrow out the None of a missing name.
                method: Any = cls.__dict__.get(operation)
                if getattr(method, _APPLIED, False):
                    setattr(cls, operation, method.__wrapped__)

    @staticmethod
    def uninstrument_protocol(protocol: Protocol) -> None:
        """Disables the instrumentation for the given protocol adapter."""
        setattr(protocol, _DISABLED, True)
