import json
from panini import app as panini_app

app = panini_app.App(
    service_name="async_request",
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
        result = await app.request(
            subject="some.request.subject.123",
            message=json.dumps(message).encode(),
        )
        log.info(result)


@app.listen("some.request.subject.123", data_type=str)
async def subject_for_requests_listener(msg):
    return {"success": True, "data": "request has been processed"}


if __name__ == "__main__":
    app.start()
