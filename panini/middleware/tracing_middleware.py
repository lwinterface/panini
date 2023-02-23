from nats.aio.msg import Msg
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from panini.middleware import Middleware
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider, Tracer
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource


class OTelTracer:
    def __init__(self, service_name: str, otel_endpoint: str, insecure_connection: bool = True, *args, **kwargs):
        self.service_name = service_name
        self.otel_endpoint = otel_endpoint
        self.insecure_connection = insecure_connection
        self.tracer = self.create_tracer()

    def create_tracer(self):
        resource = Resource(attributes={
            SERVICE_NAME: self.service_name
        })

        provider = TracerProvider(resource=resource)
        processor = BatchSpanProcessor(OTLPSpanExporter(
            endpoint=self.otel_endpoint,
            insecure=self.insecure_connection
        ))
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        return trace.get_tracer(__name__)


class TracingMiddleware(Middleware):
    def __init__(
            self,
            service_name: str,
            otel_endpoint: str,
            insecure_connection: bool,
            exclude_from_tracing=None,
            *args,
            **kwargs
    ):
        if exclude_from_tracing is None:
            exclude_from_tracing = list()
        self._otel_tracer = OTelTracer(
            service_name=service_name,
            otel_endpoint=otel_endpoint,
            insecure_connection=insecure_connection,
            *args,
            **kwargs
        )
        self.tracer: Tracer = self._otel_tracer.tracer
        self._excluded = self.objects_to_id(exclude_from_tracing)
        self.parent = TraceContextTextMapPropagator()
        super().__init__()

    def objects_to_id(self, exclude_from_tracing: list) -> list:
        return [id(o) for o in exclude_from_tracing]

    async def send_any(self, subject: str, message: Msg, send_func, *args, **kwargs):
        current_trace_config = kwargs.get("trace_config")
        if kwargs.get("use_tracing", True) and current_trace_config and current_trace_config.get(
                'span_name') and current_trace_config.get("span_attributes"):
            with self.tracer.start_as_current_span(current_trace_config["span_name"]) as span:
                for attr in current_trace_config["span_attributes"]:
                    span.set_attribute(f"colibri.{attr['key']}", attr["value"])
                return await send_func(subject, message, *args, **kwargs)
        response = await send_func(subject, message, *args, **kwargs)
        return response

    async def listen_any(self, msg: Msg, callback):
        if id(callback) in self._excluded:
            return await callback(msg)
        context = self.parent.extract(carrier=msg.headers.get("context", ""))
        span_attributes = {at: msg.headers[at] for at in msg.headers.keys() if "panini." in at}
        with self.tracer.start_as_current_span("task", context=context) as span:
            for attr_key, attr_val in span_attributes.items():
                span.set_attribute(attr_key, attr_val)
            response = await callback(msg)
            return response
