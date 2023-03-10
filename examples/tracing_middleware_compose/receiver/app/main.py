import yaml
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


# mimic config loading from yaml file
with open('tracing_middleware_config.yaml', 'r') as file:
    tracing_config = yaml.load(file, Loader=yaml.FullLoader)

tracing_config["service_name"] = "receiver_test"

if __name__ == "__main__":
    app.add_middleware(TracingMiddleware,
                       tracing_config=tracing_config)
    app.start()
