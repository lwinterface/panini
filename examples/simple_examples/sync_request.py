from panini import app as panini_app
from panini.utils.helper import start_thread

app = panini_app.App(
    service_name="ms_template_sync_by_lib",
    host="127.0.0.1",
    port=4222,
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
async def request():
    for _ in range(10):
        response = app.request_sync(subject="some.publish.subject", message=message)
        log.info(f"send message, got response {response}")


@app.timer_task(interval=2)
async def request_periodically():
    for _ in range(10):
        app.publish_sync(subject="some.publish.subject", message=message)
        log.info(f"send message from periodic task {message}")


@app.timer_task(interval=2)
async def request_from_another_thread_sync_periodically():
    start_thread(another_thread_func)


def another_thread_func():
    for _ in range(10):
        response = app.request_from_another_thread_sync(
            subject="some.publish.subject", message=message
        )
        print(f"response: {response}")


@app.listen("some.publish.subject")
def subject_for_requests_listener(msg):
    log.info(f"got request {msg.subject}")
    return {"success": True}


if __name__ == "__main__":
    app.start()
