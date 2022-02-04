import opentracing
from jaeger_client import Config
from opentracing.scope_managers.asyncio import AsyncioScopeManager
from opentracing.propagation import Format
from . import Middleware


class OpenTracingMiddleware(Middleware):
    def __init__(self, service_name, jeager_host: str, config=None, send_publish=True, listen_publish=True, send_request=True, listen_request=True):
        self.service_name = service_name
        if config is None:
            config = {  # usually read from some yaml config
                'sampler': {
                    'type': 'const',
                    'param': 1,
                    # 'type': 'probabilistic',
                    # 'param': 0.1,
                    # 'type': 'ratelimiting',
                    # 'param': 100,
                },
                'logging': True,
                'reporter_flush_interval': 1,
                'local_agent': {
                    'reporting_host': jeager_host
                    # 'reporting_host': 'localhost'
                },
                'trace_id_header': 'panini-trace-id'
            }
        self.config = Config(
            config=config,
            service_name=service_name,
            validate=True,
            scope_manager=AsyncioScopeManager(),
        )
        # this call also sets opentracing.tracer
        self.tracer = self.config.initialize_tracer()
        self.parents_spans_map = {}
        self.follows_from_spans_map = {}
        self.trace_send_publish = send_publish
        self.trace_listen_publish = listen_publish
        self.trace_send_request = send_request
        self.trace_listen_request = listen_request

    async def send_publish(self, subject, message, publish_func, **kwargs):
        if self.trace_send_publish:
            headers = kwargs.get('headers', {})
            context = kwargs.get('context', {})
            headers, span = self._trace_before_send(context, subject, headers=headers)
            kwargs['headers'] = headers
            await publish_func(subject, message, **kwargs)
            span.finish()
        else:
            await publish_func(subject, message, **kwargs)

    async def listen_publish(self, msg, cb):
        if self.trace_listen_publish:
            span = self._trace_before_listen(msg)
            await cb(msg)
            span.set_tag('subject', msg.subject)
            span.set_tag('event_type', 'listen_publish')
            span.finish()
        else:
            await cb(msg)

    async def send_request(self, subject, message, request_func, **kwargs):
        if self.trace_send_request:
            headers = kwargs.get('headers', {})
            context = kwargs.get('context', {})
            headers, span = self._trace_before_send(context, subject, headers=headers)
            kwargs['headers'] = headers
            result = await request_func(subject, message, **kwargs)
            span.finish()
        else:
            result = await request_func(subject, message, **kwargs)
        return result

    async def listen_request(self, msg, cb):
        if self.trace_listen_request:
            span = self._trace_before_listen(msg)
            result = await cb(msg)
            span.set_tag('subject', msg.subject)
            span.set_tag('event_type', 'listen_publish')
            span.finish()
        else:
            result = await cb(msg)
        return result

    def _trace_before_send(self, context, subject, headers={}):
        publish_kwargs = {
            'operation_name': context['operation_name'] if 'operation_name' in context else self.service_name#f"request-to-{subject}",
        }
        if 'parent_span' in context:
            publish_kwargs['child_of'] = context['parent_span']
        elif 'follows_from' in context:
            publish_kwargs['follows_from'] = context['follows_from']
        # else:
        #     raise Exception('send_request tracing required, expected context with "parent_span" or "follows_from"')
        outbound_span = self.tracer.start_span(**publish_kwargs)
        outbound_span.set_tag('subject', subject)
        outbound_span.set_tag('event_type', 'sent')
        self.tracer.inject(
            span_context=outbound_span.context,
            format=Format.TEXT_MAP,
            carrier=headers)
        return headers, outbound_span

    def _trace_before_listen(self, msg):
        marker = msg.headers.get('marker', {})
        parent_span = self.tracer.extract(Format.TEXT_MAP, marker)
        span = opentracing.global_tracer().start_span(f'{marker}', child_of=parent_span)
        msg.context['span'] = span
        return span