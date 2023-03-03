from panini import app as panini_app
from panini.middleware.tracing_middleware import SpanConfig, TracingMiddleware

app = panini_app.App(
    servers=["nats://nats-server:4222"],
    service_name='sender-nats',
)

log = app.logger


@app.task(interval=1)
async def default_auto_tracing():
    await app.publish("test.tracing.middleware", {})
    await app.request("test.tracing.middleware", {})
    return {"result": True}


@app.task(interval=1)
async def restrict_tracing():
    await app.publish("test.tracing.middleware.no_tracing", {}, use_tracing=False)
    await app.request("test.tracing.middleware.no_tracing", {}, use_tracing=False)
    return {"result": True}


@app.task(interval=1)
async def custom_span_tracing():
    sender_span_config = SpanConfig(
        span_name="sender_span",
        span_attributes={
            "sender_key": "sender_value",
            "publish": "true"
        }
    )
    await app.publish("test.tracing.middleware.custom_config", {}, span_config=sender_span_config)
    sender_span_config = SpanConfig(
        span_name="sender_span",
        span_attributes={
            "sender_key": "sender_value",
            "publish": "false"
        }
    )
    await app.request("test.tracing.middleware.custom_config", {}, span_config=sender_span_config)
    return {"result": True}


if __name__ == "__main__":
    app.add_middleware(TracingMiddleware,
                       service_name="sender_test",
                       otel_endpoint="open_telemetry:4317",
                       insecure_connection=True)
    app.start()
