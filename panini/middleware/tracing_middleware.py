import opentracing
from jaeger_client import Config
from opentracing.scope_managers.asyncio import AsyncioScopeManager
from opentracing.propagation import Format
from . import Middleware


class MyMiddleware(Middleware):
    def __init__(self, service_name, jeager_host='jaeger', config=None, send_publish=True, listen_publish=True, send_request=True, listen_request=True):
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
                'trace_id_header': 'anthill-trace-id'
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
            header = kwargs.get('header', {})
            if not 'context' in kwargs:
                raise Exception('send_request tracing required, expected context with "parent_span" or "follows_from"')
            header, span = self._trace_before_send(kwargs['context'], subject, header=header)
            kwargs['header'] = header
            await publish_func(subject, message, **kwargs)
            span.finish()
        else:
            await publish_func(subject, message, **kwargs)
        print('do something after publish')

    async def listen_publish(self, msg, cb):
        print('do something before listen')
        if self.trace_listen_publish:
            span = self._trace_before_listen(msg)
            await cb(msg)
            span.set_tag('subject', msg.subject)
            span.set_tag('event_type', 'listen_publish')
            span.finish()
        else:
            await cb(msg)

    async def send_request(self, subject, message, request_func, **kwargs):
        print('do something before send request')
        if self.trace_send_request:
            header = kwargs.get('header', {})
            if not 'context' in kwargs:
                raise Exception('send_request tracing required, expected context with "parent_span" or "follows_from"')
            header, span = self._trace_before_send(kwargs['context'], subject, header=header)
            kwargs['header'] = header
            result = await request_func(subject, message, **kwargs)
            span.finish()
        else:
            result = await request_func(subject, message, **kwargs)
        print('do something after send request')
        return result

    async def listen_request(self, msg, cb):
        print('do something before listen request')
        if self.trace_listen_request:
            span = self._trace_before_listen(msg)
            result = await cb(msg)
            span.set_tag('subject', msg.subject)
            span.set_tag('event_type', 'listen_publish')
            span.finish()
        else:
            result = await cb(msg)
        print('do something after listen request')
        return result

    def _trace_before_send(self, context, subject, header={}):
        publish_kwargs = {
            'operation_name': context['operation_name'] if 'operation_name' in context else f"request-to-{subject}",
        }
        if 'parent_span' in context:
            publish_kwargs['child_of'] = context['parent_span']
        elif 'follows_from' in context:
            publish_kwargs['follows_from'] = context['follows_from']
        else:
            raise Exception('send_request tracing required, expected context with "parent_span" or "follows_from"')
        outbound_span = self.tracer.start_span(**publish_kwargs)
        outbound_span.set_tag('subject', subject)
        outbound_span.set_tag('event_type', 'sent')
        opentracing.global_tracer().inject(
            span_context=outbound_span.context,
            format=Format.TEXT_MAP,
            carrier=header)
        return header, outbound_span

    def _trace_before_listen(self, msg):
        marker = msg.header.get('marker', {})
        parent_span = self.tracer.extract(Format.TEXT_MAP, marker)
        span = opentracing.global_tracer().start_span(f'{marker}', child_of=parent_span)
        msg.context['span'] = span
        return span