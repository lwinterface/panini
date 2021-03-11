from panini import app as panini_app

app = panini_app.App(
    service_name="async_reply_to",
    host="127.0.0.1",
    port=4222,
    app_strategy="asyncio",
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
async def request_to_another_subject():
    for _ in range(10):
        await app.publish(
            subject="some.subject.for.request.with.response.to" ".another.subject",
            message=message,
            reply_to="reply.to.subject",
        )
        log.warning("sent request")


@app.listen("some.subject.for.request.with.response.to.another.subject")
async def subject_for_requests_listener(msg):
    log.warning("request has been processed")
    return {"success": True, "data": "request has been processed"}


@app.listen("reply.to.subject")
async def another_subject_listener(msg):
    log.warning(f"received response: {msg.subject} {msg.data}")


if __name__ == "__main__":
    app.start()
