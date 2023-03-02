from panini import app as panini_app
from panini.middleware.tracing_middleware import TracingMiddleware, SpanConfig

app = panini_app.App(
    service_name="tracing_middleware_example",
    host="127.0.0.1",
    port=4222,
)

listener_config = SpanConfig(
    span_name="tracing_middleware_listener",
    span_attributes={
        "key_listener": "value_listener"
    }
)

publisher_config = SpanConfig(
    span_name="tracing_middelware_publisher",
    span_attributes={
        "key_publisher": "value_publisher"
    }
)

requester_config = SpanConfig(
    span_name="tracing_middelware_requester",
    span_attributes={
        "key_requester": "value_requester"
    }
)

message = {
    "key1": "value1",
}


# Publish Examples

@app.task()
async def publish_with_tracing():
    await app.publish(subject="some.publish.subject.trace", message=message, span_config=publisher_config)


@app.task()
async def publish_with_tracing_explicit():
    await app.publish(subject="some.publish.subject.trace", message=message, use_tracing=True,
                      tracing_config=publisher_config)


@app.task()
async def publish_without_tracing():
    await app.publish(subject="some.publish.subject.trace", message=message, use_tracing=False)


# Request Examples

@app.task()
async def request_with_tracing():
    await app.request(subject="some.publish.subject.trace", message=message, span_config=requester_config)


@app.task()
async def request_with_tracing_explicit():
    await app.request(subject="some.publish.subject.trace", message=message, use_tracing=True,
                      tracing_config=requester_config)


@app.task()
async def request_without_tracing():
    await app.request(subject="some.publish.subject.trace", message=message, use_tracing=False)


# Listen Examples

@app.listen("some.publish.subject.trace", span_config=listener_config, data_type=dict)
async def listen_with_tracing(msg):
    return {"success": True}


@app.listen("some.publish.subject.trace", use_tracing=True, span_config=listener_config, data_type=dict)
async def listen_with_tracing_explicit(msg):
    return {"success": True}


@app.listen("some.publish.subject.trace", use_tracing=False)
async def listen_without_tracing(msg):
    return {"success": True}


if __name__ == "__main__":
    app.add_middleware(TracingMiddleware,
                       service_name="tracing_test",
                       otel_endpoint="localhost:4317",
                       insecure_connection=True)
    app.start()
