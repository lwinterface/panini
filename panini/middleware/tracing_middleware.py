try:
    from opentelemetry import trace
    from opentelemetry.trace import SpanKind
    from opentelemetry.sdk.trace import TracerProvider, Tracer, Span
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.trace.propagation.tracecontext import (
        TraceContextTextMapPropagator,
    )
except ImportError:
    raise Exception(
        "Tracing dependencies not found, try to run `$ pip install panini[tracing]`"
    )
import inspect
import uuid
import json
from functools import wraps
from typing import Optional, List
from nats.aio.msg import Msg
from panini.app import get_app
from dataclasses import dataclass, field
from panini.middleware import Middleware
from panini.managers.event_manager import Listen
import warnings


@dataclass
class SpanConfig:
    """
     Represents a configuration for a span.
    Attributes:
        span_name (str): The name of the span.
        span_attributes (Optional[dict]): The optional dictionary of attributes for the span.
    """

    span_name: str
    span_attributes: Optional[dict]


@dataclass
class TracingEvent:
    """
    TracingEvent class represents an tracing event.

    Attributes:
        event_name (str): The name of the event.
        event_data (dict): The data associated with the event.

    Usage:
        # Create a TracingEvent object
        event = TracingEvent("my_event", {"foo": "bar"})

        # Add the event to list of events
        event_list.append(event)

        # Pass event_list to function:
        app.request(subject, message, tracing_events=event_list)

    """

    event_name: str
    event_data: dict = field(default_factory=dict)


def register_trace(**decorator_kwargs):  # the decorator
    def wrapper(f):  # a wrapper for the function
        if inspect.iscoroutinefunction(f):

            @wraps(f)
            async def decorated_function(*args, **kwargs):  # the decorated function
                ctx = trace.get_current_span().get_span_context()
                link = trace.Link(ctx)
                _tracer = trace.get_tracer(__name__)
                with _tracer.start_as_current_span(
                    decorator_kwargs.get("span_name", f"unknown-{uuid.uuid4().hex}"),
                    links=[link],
                ):
                    result = await f(*args, **kwargs)
                return result

        else:

            @wraps(f)
            def decorated_function(*args, **kwargs):  # the decorated function
                ctx = trace.get_current_span().get_span_context()
                link = trace.Link(ctx)
                _tracer = trace.get_tracer(__name__)
                with _tracer.start_as_current_span(
                    decorator_kwargs.get("span_name", f"unknown-{uuid.uuid4().hex}"),
                    links=[link],
                ):
                    result = f(*args, **kwargs)
                return result

        return decorated_function

    return wrapper


class OTELTracer:
    """
    The OTELTracer class is used to create and configure an OpenTelemetry tracer for distributed tracing.
    Attributes:
        tracing_config (dict): The configuration dictionary containing the tracing settings.
        service_name (str): The name of the service being traced.
        _config (dict): The internal configuration dictionary.
        _exporter_config (dict): The configuration for the tracer exporter.
        _provider_config (dict): The configuration for the tracer provider.
        _custom_config (dict): Additional custom configuration provided by the user.
        tracer: The OpenTelemetry tracer instance.
    Methods:
        __init__(self, tracing_config: dict, **kwargs)
            Initializes a new instance of the OTELTracer class.
            Args:
                tracing_config (dict): The configuration dictionary containing the tracing settings.
                **kwargs: Additional custom configuration parameters.
        create_tracer(self)
            Creates and configures the OpenTelemetry tracer.
            Returns:
                The initialized OpenTelemetry tracer instance.
    """

    def __init__(self, tracing_config: dict, **kwargs):
        self._config = tracing_config
        self.service_name = self._config["service_name"]
        self._exporter_config = self._config["exporter_config"]
        self._provider_config = self._config["provider_config"]
        self._custom_config = self._config["custom_config"]
        self._custom_config.update(**kwargs)
        self.tracer = self.create_tracer()

    def create_tracer(self):
        resource = Resource(attributes={SERVICE_NAME: self.service_name})
        provider = TracerProvider(resource=resource, **self._provider_config)
        processor = BatchSpanProcessor(OTLPSpanExporter(**self._exporter_config))
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        return trace.get_tracer(__name__)


class TracingMiddleware(Middleware):
    """
    Class representing a middleware for tracing requests and events in a Panini application.
    Args:
        tracing_config (dict): A dictionary containing the configuration parameters for tracing.
    Attributes:
        _otel_tracer (OTELTracer): The OpenTelemetry Tracer instance.
        tracer (Tracer): The Tracer instance extracted from _otel_tracer.
        parent (TraceContextTextMapPropagator): The Trace Context TextMap Propagator instance.
    Methods:
        _create_uuid(): Generates a UUID v4 string.
        send_any(subject: str, message: Msg, send_func, *args, **kwargs): Sends a message with tracing information.
        wildcard_match(match_key: str, subject: str) -> str: Performs a wildcard match between two strings.
        listen_any(msg: Msg, callback): Listens for events with tracing information.
    """

    def __init__(self, tracing_config: dict, **kwargs):
        otel_tracer = kwargs.get("otel_tracer")
        if otel_tracer:
            self._otel_tracer = otel_tracer
        else:
            self._otel_tracer = OTELTracer(tracing_config=tracing_config, **kwargs)
        self.tracer: Tracer = self._otel_tracer.tracer
        self.parent = TraceContextTextMapPropagator()
        self._service_name = tracing_config["service_name"]
        super().__init__()

    def _create_uuid(self) -> str:
        return uuid.uuid4().hex

    def _get_span_name(self, action: str, subject: str) -> str:
        return f"{action.upper()} {subject}"

    @staticmethod
    def extract_context_from_message(msg: Msg):
        propagator = TraceContextTextMapPropagator()
        context = propagator.extract(
            carrier=json.loads(msg.headers.get("tracing_span_carrier", "{}"))
        )
        return context

    async def trace_send_any(
        self, subject: str, message: Msg, send_func, *args, **kwargs
    ):
        verbose = kwargs.pop("verbose", False)
        carrier = {}
        context = kwargs.pop("tracing_span_carrier", None)
        span_config = kwargs.pop("span_config", None)
        use_tracing = kwargs.pop("use_tracing", True)
        action = kwargs.pop("nats_action")
        existing_events: List[TracingEvent] = kwargs.pop("tracing_events", [])
        if kwargs.pop("use_current_span", False):
            ctx = trace.get_current_span().get_span_context()
            link = [trace.Link(ctx)]
        else:
            link = []
        if not isinstance(span_config, SpanConfig):
            span_config = SpanConfig(
                span_name=self._get_span_name(action, subject), span_attributes={}
            )
        if use_tracing is True:
            self.tracer.start_span(name=span_config.span_name)
            with self.tracer.start_as_current_span(
                span_config.span_name, links=link, context=context, kind=SpanKind.SERVER
            ) as span:
                for attr_key, attr_value in span_config.span_attributes.items():
                    span.set_attribute(attr_key, attr_value)
                span.add_event(
                    action,
                    {
                        "nats.subject": subject,
                        "nats.message": json.dumps(message) if verbose else json.dumps(message)[:300],
                    },
                )
                for existing_event in existing_events:
                    span.add_event(existing_event.event_name, existing_event.event_data)
                span.set_attribute("nats.subject", subject)
                self.parent.inject(carrier=carrier)
                headers = {
                    "tracing_span_name": span_config.span_name,
                    "tracing_span_carrier": json.dumps(carrier),
                }
                kwargs.update({"headers": headers})
                try:
                    response = await send_func(subject, message, *args, **kwargs)
                    if response and verbose:
                        span.add_event("request_response", {"nats.message": response})
                    return response
                except Exception as exc:
                    span.record_exception(exc)
                    raise exc
        response = await send_func(subject, message, *args, **kwargs)
        return response

    async def send_publish(self, subject: str, message, publish_func, *args, **kwargs):
        kwargs.update({"nats_action": "send_publish"})
        response = await self.trace_send_any(
            subject, message, publish_func, *args, **kwargs
        )
        return response

    async def send_request(self, subject: str, message, request_func, *args, **kwargs):
        kwargs.update({"nats_action": "send_request"})
        response = await self.trace_send_any(
            subject, message, request_func, *args, **kwargs
        )
        return response

    @classmethod
    def wildcard_match(cls, match_key: str, subject: str) -> Optional[str]:
        """Perform a wildcard match between the match_key and the subject"""
        split_subject = subject.split(".")
        split_key = match_key.split(".")

        # if `>` at the end of match_key
        if split_key[-1] == ">":
            if (
                len(split_subject) < len(split_key) - 1
            ):  # -1 because `>` matches remaining parts
                return None
            # checking parts before `>` match
            for k, s in zip(split_key[:-1], split_subject):
                if k != "*" and k != s:
                    return None
            # parts before `>` matched in both
            return match_key

        # if not `>` at the end
        if len(split_subject) != len(split_key):
            return None

        if all(k == "*" or k == s for k, s in zip(split_key, split_subject)):
            return match_key

        return None

    async def trace_listen_any(self, msg: Msg, callback, nats_action=None):
        context = {}
        app = get_app()
        assert app is not None
        for subject in app._event_manager.subscriptions.keys():
            matched_subject = self.wildcard_match(subject, msg.subject)
            if not matched_subject:
                continue
            listen_obj_list = app._event_manager.subscriptions[matched_subject]
            listen_object: Listen
            for listen_object in listen_obj_list:
                use_tracing = listen_object._meta.get("use_tracing", True)
                if use_tracing:
                    verbose = listen_object._meta.get("verbose", False)
                    if (
                        id(callback) == id(listen_object.callback)
                        and callback.__name__ == listen_object.callback.__name__
                    ):
                        headers = msg.headers
                        if headers:
                            context = self.parent.extract(
                                carrier=json.loads(
                                    msg.headers.get("tracing_span_carrier", "{}")
                                )
                            )
                        span_config = listen_object._meta.get("span_config")
                        if not isinstance(span_config, SpanConfig):
                            span_config = SpanConfig(
                                span_name=self._get_span_name(nats_action, subject),
                                span_attributes={},
                            )
                        with self.tracer.start_as_current_span(
                            span_config.span_name, context=context, kind=SpanKind.CLIENT
                        ) as span:
                            for (
                                attr_key,
                                attr_val,
                            ) in span_config.span_attributes.items():
                                span.set_attribute(attr_key, attr_val)
                            span.set_attribute("nats.subject", subject)
                            span.add_event(
                                nats_action,
                                {
                                    "nats.subject": subject,
                                    "nats.message": json.dumps(msg.data) if verbose else json.dumps(msg.data)[:300],
                                },
                            )
                            try:
                                response = await callback(msg)
                                if response and "tracing_events" in response.keys():
                                    tracing_events: List[TracingEvent] = response.pop(
                                        "tracing_events", []
                                    )
                                    for event in tracing_events:
                                        span.add_event(
                                            event.event_name, event.event_data
                                        )
                                if verbose:
                                    span.add_event("listen_response", response)
                            except Exception as exc:
                                span.record_exception(exception=exc)
                                raise exc
                    else:
                        warnings.warn(
                            "TracingMiddleware logic on listener doesn't work, it should be placed first when adding middlewares!"
                        )
                        response = await callback(msg)
                else:
                    response = await callback(msg)
                return response

    async def listen_publish(self, msg, callback):
        response = await self.trace_listen_any(
            msg, callback, nats_action="listen_publish"
        )
        return response

    async def listen_request(self, msg, callback):
        response = await self.trace_listen_any(
            msg, callback, nats_action="listen_request"
        )
        return response
