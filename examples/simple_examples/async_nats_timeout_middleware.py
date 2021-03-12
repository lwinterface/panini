from panini import app as panini_app
from panini.middleware.nats_timeout import NATSTimeoutMiddleware

app = panini_app.App(
    service_name="async_nats_timeout_middleware",
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
async def request_periodically():
    log.info("Send request to not existing subject - expecting NATS Timeout")
    response = await app.request(subject="not.existing.subject", message=message)
    log.info(f"response message from periodic task: {response}")


@app.listen("handle.nats.timeout.subject")
async def handle_timeout(msg):
    log.error(f"NATS timeout handled: {msg.data}")
    return {"success": True, "data": "successfully handled NATS timeout"}


if __name__ == "__main__":
    app.add_middleware(
        NATSTimeoutMiddleware,
        subject="handle.nats.timeout.subject",
        send_func_type="request",
    )
    app.start()
