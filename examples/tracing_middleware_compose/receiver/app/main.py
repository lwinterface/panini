from nats.aio.msg import Msg
from panini import app as panini_app
from panini.middleware.tracing_middleware import TracingMiddleware, SpanConfig

app = panini_app.App(
    servers=["nats://nats-server:4222"],
    service_name='receiver-nats',
)

log = app.logger


@app.listen("test.tracing.middleware")
async def default_auto_tracing(msg: Msg):
    return {"result": True}


@app.listen("test.tracing.middleware.no_tracing", use_tracing=False)
async def restrict_tracing(msg: Msg):
    return {"result": True}


receiver_span_config = SpanConfig(
    span_name="receiver_span",
    span_attributes={
        "receiver_key": "receiver_value"
    }
)


@app.listen("test.tracing.middleware.custom_config", span_config=receiver_span_config)
async def custom_span_tracing(msg: Msg):
    return {"result": True}


if __name__ == "__main__":
    app.add_middleware(TracingMiddleware,
                       service_name="receiver_test",
                       otel_endpoint="open_telemetry:4317",
                       insecure_connection=True)
    app.start()
