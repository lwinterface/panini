from panini import app as panini_app

app = panini_app.App(
    service_name="ms_template_sync_by_lib",
    host="127.0.0.1",
    port=4222,
    app_strategy="sync",
)

log = app.logger

message = {
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
        app.publish_sync(subject="some.publish.subject", message=message)
        log.info(f"send message {message}")


@app.timer_task(interval=2)
def publish_periodically():
    for _ in range(10):
        app.publish_sync(subject="some.publish.subject", message=message)
        log.info(f"send message from periodic task {message}")


@app.listen("some.publish.subject")
def subject_for_requests_listener(msg):
    log.info(f"got message {msg.subject}")


if __name__ == "__main__":
    app.start()
