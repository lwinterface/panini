import asyncio

import yaml
from nats.aio.msg import Msg
from panini import app as panini_app
from panini.middleware.tracing_middleware import (
    TracingMiddleware,
    SpanConfig,
    TracingEvent,
)

app = panini_app.App(
    servers=["nats://nats-server:4222"],
    service_name="receiver-nats",
)

log = app.logger


@app.listen("test.tracing.middleware")
async def default_auto_tracing(msg: Msg):
    return {"result": True}


@app.listen("test.tracing.middleware.with.events")
async def listen_with_events(msg: Msg):
    event = TracingEvent(
        event_name="tracing_event_01",
        event_data={"took_ms": 15, "request_from": "frontend", "request_type": "POST"},
    )
    return {"success": True, "data": [1, 2, 3, 4, 5], "tracing_events": [event]}


@app.listen("test.tracing.middleware.with.exceptions")
async def listen_with_exception(msg: Msg):
    raise Exception("test exception raised!")


@app.listen("test.tracing.middleware.no_tracing", use_tracing=False)
async def restrict_tracing(msg: Msg):
    return {"result": True}


receiver_span_config = SpanConfig(
    span_name="receiver_span", span_attributes={"receiver_key": "receiver_value"}
)


@app.listen("test.tracing.middleware.custom_config", span_config=receiver_span_config)
async def custom_span_tracing(msg: Msg):
    return {"result": True}


######################## EXAMPLE OF TRACING WITHIN MICROSERVICE ########################
from panini.middleware.tracing_middleware import register_trace


@register_trace(span_name="job2")
async def job_2(price: int):
    await asyncio.sleep(1)  # heavy work
    if price >= 1:
        await app.publish(
            "test.tracing.inside.microservice.success", {}, use_current_span=True
        )
        return True
    else:
        await app.publish("test.tracing.inside.microservice.fail", {})
        return False


@register_trace(span_name="job1")
async def job_1(msg: Msg):
    return await job_2(msg.data.get("price"))


@app.listen("test.tracing.inside.microservice.query")
async def tracing_multiple_layers(msg: Msg):
    result = await job_1(msg)
    return {"result": result}


@app.listen("ignore.this.subject")
async def ignore_this_subect(msg: Msg):
    return {"result": "This should not be in tracing"}


@app.listen("ignore.this.subject.wildcard.anything")
async def ignore_this_subject_wildcard(msg: Msg):
    return {"result": "This should not be in tracing"}


@app.listen("ignore.this.subject.and.more.>")
async def ignore_this_subject_and_more(msg: Msg):
    return {"result": "This should not be in tracing"}


@app.listen("ignore.only.listen.subject")
async def ignore_only_listen_subject(msg: Msg):
    return {"result": "This should not be in tracing"}


@app.listen("ignore.only.send.subject")
async def ignore_only_send_subject(msg: Msg):
    return {"result": "Only listen should be in tracing"}


@app.listen("check.other.subjects")
async def check_other_subjects(msg: Msg):
    return {"result": "Both send and listen should be in tracing"}


# mimic config loading from yaml file
with open("tracing_middleware_config.yaml", "r") as file:
    tracing_config = yaml.load(file, Loader=yaml.FullLoader)

tracing_config["service_name"] = "receiver_test"

if __name__ == "__main__":
    app.add_middleware(TracingMiddleware, tracing_config=tracing_config)
    app.start()
