from nats.aio.errors import ErrTimeout

from panini import app as panini_app
from panini.middleware import Middleware
from panini.middleware.error_middleware import ErrorMiddleware

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
    response = await app.request(subject="not.existing.subject", message=message)
    log.warning(f"response message from periodic task: {response}")


@app.listen("handle.nats.timeout.subject")
async def handle_timeout(msg):
    log.error(f"NATS timeout handled: {msg.data['error']}")
    return {'success': True, "data": "successfully handled NATS timeout"}


if __name__ == "__main__":
    handle_nats_timeout_subject = "handle.nats.timeout.subject"

    async def handle_nats_timeout(error: Exception):
        response = await app.request(handle_nats_timeout_subject, {"error": str(error)})
        log.info(f"Response from response handle_timeout function: {response}")

    app.add_middleware(ErrorMiddleware, error=ErrTimeout, callback=handle_nats_timeout)
    app.start()
