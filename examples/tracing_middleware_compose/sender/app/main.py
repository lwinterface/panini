import yaml
from nats.aio.msg import Msg

from panini import app as panini_app
from panini.middleware.tracing_middleware import (
    SpanConfig,
    TracingMiddleware,
    TracingEvent,
)

app = panini_app.App(
    servers=["nats://nats-server:4222"],
    service_name="sender-nats",
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
        span_attributes={"sender_key": "sender_value", "publish": "true"},
    )
    await app.publish(
        "test.tracing.middleware.custom_config", {}, span_config=sender_span_config
    )
    sender_span_config = SpanConfig(
        span_name="sender_span",
        span_attributes={"sender_key": "sender_value", "publish": "false"},
    )
    await app.request(
        "test.tracing.middleware.custom_config", {}, span_config=sender_span_config
    )
    return {"result": True}


@app.task()
async def tracing_with_events():
    event = TracingEvent()
    await app.publish(
        "test.tracing.middleware.with.events",
        {"data": [1, 2, 3, 4, 5]},
        tracing_events=[event],
    )


@app.task()
async def exception_tracing_in_listen_function():
    await app.publish("test.tracing.middleware.with.exception", {})


@app.task()
async def exception_tracing_in_send_function():
    await app.publish("test", 1)


######################## EXAMPLE OF TRACING WITHIN MICROSERVICE ########################
@app.task()
async def tracing_within_microservice():
    res = await app.request("test.tracing.inside.microservice.query", {"price": 2})
    log.info(f"Result from tracing within microservice: {res}")


@app.listen("test.tracing.inside.microservice.*")
async def success_or_fail_result(msg: Msg):
    _, _, _, _, success = msg.subject.split(".")
    if success == "success":
        log.info("Got success message")
    else:
        log.info("Got fail message")


@app.task()
async def ignoring_subjects_via_config():
    await app.publish(
        "ignore.this.subject", {"result": "This should not be in tracing"}
    )
    await app.publish(
        "ignore.this.subject.wildcard.anything",
        {"result": "This should not be in tracing"},
    )
    await app.publish(
        "ignore.this.subject.and.more.of.it",
        {"result": "This should not be in tracing"},
    )
    await app.publish(
        "ignore.this.subject.and.more.of.it",
        {"result": "Only send should be in tracing"},
    )
    await app.publish(
        "ignore.only.send.subject", {"result": "Only listen should be in tracing"}
    )
    await app.publish(
        "check.other.subjects", {"result": "Both send and listen should be in tracing"}
    )


# mimic config loading from yaml file
with open("tracing_middleware_config.yaml", "r") as file:
    tracing_config = yaml.load(file, Loader=yaml.FullLoader)

tracing_config["service_name"] = "sender_test"

if __name__ == "__main__":
    app.add_middleware(TracingMiddleware, tracing_config=tracing_config)
    app.start()
