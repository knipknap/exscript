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
OpenTelemetry instrumentation for Exscript.

Automatically creates spans and metrics for ``Protocol.connect``,
``login``, ``send``, ``execute`` and ``close`` (plus the same on
``Netconf``).

Usage::

    from Exscript.contrib.otel import ExscriptInstrumentor

    ExscriptInstrumentor().instrument()
"""

from __future__ import annotations

import functools
import types
from collections.abc import Callable, Collection
from timeit import default_timer

from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.metrics import Histogram, get_meter
from opentelemetry.trace import SpanKind, Tracer, get_tracer, set_span_in_context
from opentelemetry.trace.span import Span

from Exscript.protocols.protocol import Protocol

# TODO (Netconf): Check whether Netconf is now similar enough to Protocol.
try:
    from Exscript.protocols.netconf import Netconf
except ImportError:  # ncclient may not be installed
    Netconf = None  # type: ignore[misc,assignment]

from Exscript.version import __version__ as _exscript_version

# ---------------------------------------------------------------------------
# Public type aliases
# ---------------------------------------------------------------------------
_RequestHookT = Callable[[Span, Protocol], None] | None
_ResponseHookT = Callable[[Span, Protocol], None] | None

# Sentinel attribute set on patched methods
_APPLIED_ATTR = "opentelemetry_instrumentation_exscript_applied"
# Attribute stored on the Protocol *instance* by the connect wrapper
_CONNECT_SPAN_ATTR = "opentelemetry_instrumentation_exscript_connect_span"

# Methods to instrument — same set for Protocol and Netconf
_INSTRUMENTED_METHODS = ("connect", "login", "authenticate", "close", "send", "execute")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _get_parent_span(proto: Protocol) -> Span | None:
    """Return the span started by ``connect``, if any."""
    return getattr(proto, _CONNECT_SPAN_ATTR, None)


def _get_protocol_attributes(proto: Protocol) -> dict:
    """Collect common span attributes from a Protocol instance."""
    attrs: dict = {
        "protocol.type": proto.__class__.__name__,
        "protocol.host": proto.host,
        "protocol.port": proto.port,
        "protocol.encoding": proto.encoding,
    }
    # These calls may fail before connect — be defensive
    try:
        attrs["protocol.timeout"] = proto.get_timeout()
    except Exception:  # noqa: BLE001, S110
        pass
    try:
        attrs["protocol.connect_timeout"] = proto.get_connect_timeout()
    except Exception:  # noqa: BLE001, S110
        pass
    try:
        attrs["protocol.os"] = proto.guess_os()
    except Exception:  # noqa: BLE001, S110
        pass
    try:
        prompt = proto.get_prompt()
        attrs["protocol.prompt"] = (
            [getattr(p, "pattern", str(p)) for p in prompt]
            if isinstance(prompt, (list, tuple))
            else getattr(prompt, "pattern", str(prompt))
        )
    except Exception:  # noqa: BLE001, S110
        pass
    try:
        err_prompt = proto.get_error_prompt()
        attrs["protocol.error_prompt"] = (
            [getattr(p, "pattern", str(p)) for p in err_prompt]
            if isinstance(err_prompt, (list, tuple))
            else getattr(err_prompt, "pattern", str(err_prompt))
        )
    except Exception:  # noqa: BLE001, S110
        pass
    try:
        attrs["protocol.protocol_authenticated"] = proto.is_protocol_authenticated()
    except Exception:  # noqa: BLE001, S110
        pass
    try:
        attrs["protocol.app_authenticated"] = proto.is_app_authenticated()
    except Exception:  # noqa: BLE001, S110
        pass
    try:
        attrs["protocol.app_authorized"] = proto.is_app_authorized()
    except Exception:  # noqa: BLE001, S110
        pass
    return attrs


def _span_name(protocol_name: str, action: str) -> str:
    return f"{protocol_name.strip()} {action.strip()}"


# ---------------------------------------------------------------------------
# Generic wrapper factory
# ---------------------------------------------------------------------------
def _make_wrapper(
    original,
    action: str,
    tracer: Tracer,
    duration_histogram: Histogram,
    request_hook: _RequestHookT,
    response_hook: _ResponseHookT,
):
    """Return an instrumented replacement for *original* method."""

    @functools.wraps(original)
    def wrapper(self, *args, **kwargs):
        protocol_name = self.__class__.__name__
        name = _span_name(protocol_name, action)

        # --- span attributes ---
        span_attributes: dict = {"protocol.type": protocol_name}
        span_attributes.update(_get_protocol_attributes(self))

        # action-specific attributes
        if action == "connect":
            hostname = kwargs.get("hostname") or (args[0] if args else None)
            port = kwargs.get("port") or (args[1] if len(args) > 1 else None)
            if hostname:
                span_attributes["protocol.host"] = hostname
            if port:
                span_attributes["protocol.port"] = port
        elif action in ("login", "authenticate"):
            account = kwargs.get("account") or (args[0] if args else None)
            app_account = kwargs.get("app_account") or (args[1] if args else None)
            if account is not None:
                try:
                    span_attributes["protocol.username"] = account.get_name()
                except Exception:  # noqa: BLE001, S110
                    pass
            if app_account is not None:
                try:
                    span_attributes["protocol.app_username"] = app_account.get_name()
                except Exception:  # noqa: BLE001, S110
                    pass
        elif action == "close":
            force = kwargs.get("force", False) or (args[0] if args else False)
            span_attributes["protocol.force_close"] = force
        elif action in ("send", "execute"):
            data = kwargs.get("data")
            command = kwargs.get("command", data) or (args[0] if args else None)
            if command is not None:
                span_attributes["protocol.command"] = command

        metric_labels = {"protocol.type": protocol_name}

        # --- connect uses a long-lived span (ended in close) ---
        if action == "connect":
            span = tracer.start_span(name, kind=SpanKind.CLIENT, attributes=span_attributes)
            exception = None
            if callable(request_hook):
                request_hook(span, self)
            start_time = default_timer()
            try:
                result = original(self, *args, **kwargs)
            except Exception as exc:  # noqa: BLE001
                exception = exc
                result = getattr(exc, "response", None)
            finally:
                elapsed = max(round((default_timer() - start_time) * 1000), 0)

            if callable(response_hook):
                response_hook(span, self, result)
            duration_histogram.record(elapsed, attributes=metric_labels)

            if exception is not None:
                raise exception.with_traceback(exception.__traceback__)

            # Store so child spans can use it as parent
            setattr(self, _CONNECT_SPAN_ATTR, span)
            return result

        # --- all other actions use a child span scoped to the call ---
        parent = _get_parent_span(self)
        ctx = set_span_in_context(parent) if parent else None

        span_kwargs: dict = {
            "kind": SpanKind.CLIENT,
            "attributes": span_attributes,
        }
        if ctx:
            span_kwargs["context"] = ctx

        with tracer.start_as_current_span(name, **span_kwargs) as span:
            exception = None
            if callable(request_hook):
                request_hook(span, self)
            start_time = default_timer()
            try:
                result = original(self, *args, **kwargs)
            except Exception as exc:  # noqa: BLE001
                exception = exc
                result = getattr(exc, "response", None)
            finally:
                elapsed = max(round((default_timer() - start_time) * 1000), 0)

            # Capture response on execute, send does not update response by design!
            if action == "execute":
                try:
                    span.set_attribute("protocol.response", str(self.response))
                except Exception:  # noqa: BLE001, S110
                    pass

            if callable(response_hook):
                response_hook(span, self, result)
            duration_histogram.record(elapsed, attributes=metric_labels)

            if exception is not None:
                raise exception.with_traceback(exception.__traceback__)

        # End the connect span when close is called
        if action == "close" and parent is not None:
            try:
                parent.end()
            except Exception:  # noqa: BLE001, S110
                pass

        return result

    setattr(wrapper, _APPLIED_ATTR, True)
    return wrapper


# ---------------------------------------------------------------------------
# Patch / un-patch logic
# ---------------------------------------------------------------------------
def _instrument_class(
    cls,
    tracer: Tracer,
    duration_histogram: Histogram,
    request_hook: _RequestHookT,
    response_hook: _ResponseHookT,
):
    """Monkey-patch all target methods on *cls*."""
    for method_name in _INSTRUMENTED_METHODS:
        original = getattr(cls, method_name, None)
        if original is None:
            continue
        if getattr(original, _APPLIED_ATTR, False):
            continue  # already instrumented
        wrapped = _make_wrapper(
            original,
            method_name,
            tracer,
            duration_histogram,
            request_hook,
            response_hook,
        )
        setattr(cls, method_name, wrapped)


def _uninstrument_class(cls):
    """Restore original methods on *cls*."""
    for method_name in _INSTRUMENTED_METHODS:
        func = getattr(cls, method_name, None)
        if func is None or not getattr(func, _APPLIED_ATTR, False):
            continue
        setattr(cls, method_name, func.__wrapped__)


# ---------------------------------------------------------------------------
# Public instrumentor
# ---------------------------------------------------------------------------
class ExscriptInstrumentor(BaseInstrumentor):
    """OpenTelemetry instrumentor for Exscript Protocol & Netconf.

    Usage::

        ExscriptInstrumentor().instrument()
        # optional hooks:
        ExscriptInstrumentor().instrument(
            request_hook=my_request_hook,
            response_hook=my_response_hook,
        )
    """

    def instrumentation_dependencies(self) -> Collection[str]:
        return ("exscript",)

    def _instrument(self, **kwargs):
        tracer_provider = kwargs.get("tracer_provider")
        tracer = get_tracer(
            __name__,
            _exscript_version,
            tracer_provider,
        )
        meter_provider = kwargs.get("meter_provider")
        meter = get_meter(__name__, _exscript_version, meter_provider)
        duration_histogram = meter.create_histogram(
            name="exscript.client.duration",
            unit="ms",
            description="Duration of Exscript protocol operations",
        )
        request_hook = kwargs.get("request_hook")
        response_hook = kwargs.get("response_hook")

        _instrument_class(
            Protocol,
            tracer,
            duration_histogram,
            request_hook,
            response_hook,
        )
        if Netconf is not None:
            _instrument_class(
                Netconf,
                tracer,
                duration_histogram,
                request_hook,
                response_hook,
            )

    def _uninstrument(self, **kwargs):
        _uninstrument_class(Protocol)
        if Netconf is not None:
            _uninstrument_class(Netconf)

    @staticmethod
    def uninstrument_protocol(protocol):
        """Disable instrumentation on a specific *protocol* instance."""
        for method_name in _INSTRUMENTED_METHODS:
            func = getattr(protocol, method_name, None)
            if func is None or not getattr(func, _APPLIED_ATTR, False):
                continue
            original = types.MethodType(func.__wrapped__, protocol)
            setattr(protocol, method_name, original)
