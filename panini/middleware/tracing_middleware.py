import uuid
import json
from typing import Optional
from nats.aio.msg import Msg
from panini.app import get_app
from opentelemetry import trace
from dataclasses import dataclass
from panini.middleware import Middleware
from panini.managers.event_manager import Listen
from opentelemetry.sdk.trace import TracerProvider, Tracer
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator


@dataclass
class TraceConfig:
    span_name: str
    span_attributes: Optional[dict]


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
            *args,
            **kwargs
    ):
        self._otel_tracer = OTelTracer(
            service_name=service_name,
            otel_endpoint=otel_endpoint,
            insecure_connection=insecure_connection,
            *args,
            **kwargs
        )
        self.tracer: Tracer = self._otel_tracer.tracer
        self.parent = TraceContextTextMapPropagator()
        super().__init__()

    def _create_uuid(self) -> str:
        return uuid.uuid4().hex

    async def send_any(self, subject: str, message: Msg, send_func, *args, **kwargs):
        carrier = {}
        headers = {}
        current_trace_config = kwargs.get("trace_config")
        use_tracing = kwargs.get("use_tracing", True)
        if use_tracing is True and not isinstance(current_trace_config, TraceConfig):
            raise Exception("Trace config should be explicitly provided!")
        if use_tracing is True and current_trace_config and current_trace_config.span_name and current_trace_config.span_attributes:
            with self.tracer.start_as_current_span(
                    current_trace_config.span_name if current_trace_config.span_name else self._create_uuid()) as span:
                for attr_key, attr_value in current_trace_config.span_attributes.items():
                    span.set_attribute(attr_key, attr_value)
                self.parent.inject(carrier=carrier)
                headers = {
                    "tracing_span_name": current_trace_config.span_name,
                    "tracing_span_carrier": json.dumps(carrier)
                }
        if "use_tracing" in kwargs:
            del kwargs['use_tracing']
        response = await send_func(subject, message, headers=headers)
        return response

    async def listen_any(self, msg: Msg, callback):
        app = get_app()
        assert app is not None
        listen_obj_list = app._event_manager.subscriptions[msg.subject]
        for index in range(0, len(listen_obj_list)):
            listen_obj: Listen = listen_obj_list[index]
            callback_info = listen_obj._meta.get("callback", {})
            if id(callback) == callback_info.get("callback_id", "") and callback.__name__ == callback_info.get(
                    "callback_name", "") and listen_obj._meta.get("use_tracing", True) is True:
                context = self.parent.extract(carrier=json.loads(msg.headers.get("tracing_span_carrier", "")))
                span_name = msg.headers.get("span_name", "")
                current_trace_config = listen_obj._meta.get("trace_config")
                if not isinstance(current_trace_config, TraceConfig) or not context:
                    raise Exception("Trace config or context should be explicitly provided!")
                span_attributes = {at: msg.headers[at] for at in msg.headers.keys() if "tracing." in at}
                if current_trace_config.span_attributes:
                    span_attributes.update(current_trace_config.span_attributes)
                with self.tracer.start_as_current_span(span_name if span_name else self._create_uuid(),
                                                       context=context) as span:
                    for attr_key, attr_val in span_attributes.items():
                        span.set_attribute(attr_key, attr_val)
                    response = await callback(msg)
                    return response
        return await callback(msg)
