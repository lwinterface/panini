import os
from panini import app as panini_app
from panini.middleware.opentracing_middleware import OpenTracingMiddleware

SERVICE_NAME = "microservice1"
JEAGER_HOST = 'jeager:6831' if 'HOSTNAME' in os.environ else '127.0.0.1:6831'

app = panini_app.App(
    service_name=SERVICE_NAME,
    host="nats-server" if "HOSTNAME" in os.environ else "127.0.0.1",
    port=4222,
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


@app.timer_task(interval=5)
async def publish_periodically():
    await app.publish(subject="some.publish.subject", message=msg)
    log.info(f"send message from periodic task {msg}")


if __name__ == "__main__":
    app.add_middleware(
        OpenTracingMiddleware,
        service_name=SERVICE_NAME,
        jeager_host=JEAGER_HOST
    )
    app.start()
