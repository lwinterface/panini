import yaml

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


# mimic config loading from yaml file
with open('tracing_middleware_config.yaml', 'r') as file:
    tracing_config = yaml.load(file, Loader=yaml.FullLoader)

tracing_config["service_name"] = "sender_test"

if __name__ == "__main__":
    app.add_middleware(TracingMiddleware,
                       tracing_config=tracing_config)
    app.start()
