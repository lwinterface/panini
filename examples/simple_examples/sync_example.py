from anthill import app as ant_app

app = ant_app.App(
    service_name="ms_template_sync_by_lib",
    host="127.0.0.1",
    port=4222,
    app_strategy="sync",
)

log = app.logger

msg = {
    "key1": "value1",
    "key2": 2,
    "key3": 3.0,
    "key4": [1, 2, 3, 4],
    "key5": {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5},
    "key6": {"subkey1": "1", "subkey2": 2, "3": 3, "4": 4, "5": 5},
    "key7": None,
}


@app.task()
def publish():
    for _ in range(10):
        # app.publish_sync(topic="some.publish.topic", message=msg)
        app.publish_sync(topic="some.request.topic", message=msg, reply_to="some.publish.topic")
        # data = app.request_sync(topic="some.request.topic", message=msg)
        # log.warning(f"data from request: {data}")
        log.warning(f"send message {msg}")


# @app.timer_task(interval=2)
# def publish_periodically():
#     for _ in range(10):
#         app.publish_sync(topic="some.publish.topic", message=msg)
#         log.warning(f"send message from periodic task {msg}")


@app.listen("some.publish.topic")
def topic_for_requests_listener(topic, message):
    log.warning(f"got message {message}")


@app.listen("some.request.topic")
def topic_for_requests(topic, message):
    log.warning(f"got request {message}")
    return {"data": 1}


if __name__ == "__main__":
    app.start()
