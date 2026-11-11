import importlib.metadata
import unittest
from unittest import mock

from Exscript import Account
from Exscript.emulators import VirtualDevice
from Exscript.protocols import Dummy

try:
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import InMemoryMetricReader
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
    from opentelemetry.trace import SpanKind, StatusCode

    from Exscript.contrib.otel import ExscriptInstrumentor
except ImportError:  # the optional "otel" extra is not installed
    ExscriptInstrumentor = None

PASSWORD = 'S3cr3t-P@ss'


class Child(Dummy):
    """An adapter whose override calls the instrumented base method."""

    def authenticate(self, *args, **kwargs):
        return super().authenticate(*args, **kwargs)


@unittest.skipIf(ExscriptInstrumentor is None, 'requires the "otel" extra')
class OtelTest(unittest.TestCase):
    def instrument(self, **kwargs):
        self.exporter = InMemorySpanExporter()
        tracer_provider = TracerProvider()
        tracer_provider.add_span_processor(SimpleSpanProcessor(self.exporter))
        self.reader = InMemoryMetricReader()
        instrumentor = ExscriptInstrumentor()
        instrumentor.instrument(
            tracer_provider=tracer_provider,
            meter_provider=MeterProvider(metric_readers=[self.reader]),
            skip_dep_check=True,
            **kwargs,
        )
        self.addCleanup(instrumentor.uninstrument)

    def runSession(self, cls=Dummy, disable=False):
        device = VirtualDevice('r1', echo=False, strict=False)
        device.add_command('show run', 'snmp-server community PRIVATE RW')
        conn = cls(device=device, connect_rate_limit=0)
        if disable:
            ExscriptInstrumentor.uninstrument_protocol(conn)
        conn.connect('r1')
        conn.login(Account('admin', PASSWORD, needs_lock=False))  # a positional account
        conn.execute('show run')
        conn.close(force=True)

    def spans(self, name=None):
        spans = self.exporter.get_finished_spans()
        return [span for span in spans if name is None or span.name == name]

    def testSpans(self):
        self.instrument()
        self.runSession()
        names = {span.name for span in self.spans()}
        self.assertLessEqual(
            {'Dummy connect', 'Dummy login', 'Dummy execute', 'Dummy close'}, names
        )
        (execute,) = self.spans('Dummy execute')
        self.assertEqual(execute.kind, SpanKind.CLIENT)
        self.assertEqual(execute.attributes['server.address'], 'r1')
        self.assertEqual(execute.attributes['exscript.protocol'], 'Dummy')
        self.assertEqual(execute.attributes['exscript.operation'], 'execute')
        sends = self.spans('Dummy send')
        children = [span for span in sends if span.parent.span_id == execute.context.span_id]
        self.assertEqual(len(children), 1)

    def testNoPayloadByDefault(self):
        self.instrument()
        self.runSession()
        exported = [str(value) for span in self.spans() for value in span.attributes.values()]
        leaks = [
            value
            for value in exported
            if PASSWORD in value or 'show run' in value or 'PRIVATE' in value
        ]
        self.assertEqual(leaks, [])

    def testCapturePayload(self):
        self.instrument(capture_payload=True, max_payload_length=12)
        self.runSession()
        (execute,) = self.spans('Dummy execute')
        self.assertEqual(execute.attributes['exscript.command'], 'show run')
        self.assertEqual(execute.attributes['exscript.response'], 'snmp-server ...')
        commands = [span.attributes.get('exscript.command') for span in self.spans('Dummy send')]
        self.assertIn('<secret>', commands)
        exported = [str(value) for span in self.spans() for value in span.attributes.values()]
        self.assertEqual([value for value in exported if PASSWORD in value], [])

    def testFailedConnectEndsItsSpan(self):
        self.instrument()
        conn = Dummy(connect_rate_limit=0)
        with mock.patch.object(Dummy, '_connect', side_effect=OSError('unreachable')):
            self.assertRaises(OSError, conn.connect, 'r1')
        (span,) = self.spans('Dummy connect')
        self.assertEqual(span.status.status_code, StatusCode.ERROR)
        self.assertEqual(span.attributes['error.type'], 'OSError')

    def testDurationMetric(self):
        self.instrument()
        self.runSession()
        (metric,) = [
            metric
            for resource in self.reader.get_metrics_data().resource_metrics
            for scope in resource.scope_metrics
            for metric in scope.metrics
        ]
        self.assertEqual(metric.name, 'exscript.client.operation.duration')
        self.assertEqual(metric.unit, 's')
        operations = {point.attributes['exscript.operation'] for point in metric.data.data_points}
        self.assertLessEqual({'connect', 'login', 'send', 'execute', 'close'}, operations)

    def testOverrideCallingSuperCreatesOneSpan(self):
        self.instrument()
        self.runSession(Child)
        self.assertEqual(len(self.spans('Child authenticate')), 1)

    def testUninstrumentProtocol(self):
        self.instrument()
        self.runSession(disable=True)
        self.assertEqual(self.spans(), [])

    def testUninstrument(self):
        original = Dummy.connect
        self.instrument()
        self.assertIsNot(Dummy.connect, original)
        ExscriptInstrumentor().uninstrument()
        self.assertIs(Dummy.connect, original)

    def testHooks(self):
        calls = []

        def request_hook(span, conn):
            calls.append(('request', span.name))
            span.set_attribute('test.hook', 'request')

        def response_hook(span, conn, result):
            calls.append(('response', span.name, result))

        self.instrument(request_hook=request_hook, response_hook=response_hook)
        conn = Dummy(device=VirtualDevice('r1', echo=False, strict=False), connect_rate_limit=0)
        conn.connect('r1')
        conn.close(force=True)
        expected = [
            ('request', 'Dummy connect'),
            ('response', 'Dummy connect', True),
            ('request', 'Dummy close'),
            ('response', 'Dummy close', None),
        ]
        self.assertEqual(calls, expected)
        self.assertEqual({span.attributes['test.hook'] for span in self.spans()}, {'request'})

    def testFailedCallGetsNoResponseHook(self):
        responses = []
        self.instrument(response_hook=lambda span, conn, result: responses.append(result))
        conn = Dummy(connect_rate_limit=0)
        with mock.patch.object(Dummy, '_connect', side_effect=OSError('unreachable')):
            self.assertRaises(OSError, conn.connect, 'r1')
        self.assertEqual(responses, [])

    def testArgumentsThatDoNotFit(self):
        # The method raises the TypeError, and no span is created.
        self.instrument()
        conn = Dummy(connect_rate_limit=0)
        self.assertRaises(TypeError, conn.execute)
        self.assertRaises(TypeError, conn.connect, 'r1', 23, 'extra')
        self.assertEqual(self.spans(), [])

    def testWithoutAddress(self):
        # The address and the port are set only if they are known.
        self.instrument()
        Dummy(connect_rate_limit=0).close()
        (span,) = self.spans('Dummy close')
        self.assertNotIn('server.address', span.attributes)
        self.assertNotIn('server.port', span.attributes)

    def testDependencyCheck(self):
        # Exscript is installed, so instrument() works without skip_dep_check.
        try:
            importlib.metadata.version('Exscript')
        except importlib.metadata.PackageNotFoundError:
            self.skipTest('Exscript is not installed')
        instrumentor = ExscriptInstrumentor()
        self.assertEqual(instrumentor.instrumentation_dependencies(), ('exscript',))
        original = Dummy.connect
        instrumentor.instrument()
        self.addCleanup(instrumentor.uninstrument)
        self.assertIsNot(Dummy.connect, original)
